# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

__dir__ = os.path.dirname(__file__)
sys.path.append(__dir__)
sys.path.append(os.path.join(__dir__, '..'))

import numpy as np
from .locality_aware_nms import nms_locality
from ppocr.utils.e2e_utils.extract_textpoint import *
from ppocr.utils.e2e_utils.ski_thin import *
from ppocr.utils.e2e_utils.visual import *
import paddle
import cv2
import time


class PGPostProcess(object):
    """
    The post process for SAST.
    """

    def __init__(self,
                 score_thresh=0.5,
                 nms_thresh=0.2,
                 sample_pts_num=2,
                 shrink_ratio_of_width=0.3,
                 expand_scale=1.0,
                 tcl_map_thresh=0.5,
                 **kwargs):
        self.result_path = ""
        self.valid_set = 'totaltext'
        self.Lexicon_Table = [
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C',
            'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
            'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
        ]
        self.score_thresh = score_thresh
        self.nms_thresh = nms_thresh
        self.sample_pts_num = sample_pts_num
        self.shrink_ratio_of_width = shrink_ratio_of_width
        self.expand_scale = expand_scale
        self.tcl_map_thresh = tcl_map_thresh

        # c++ la-nms is faster, but only support python 3.5
        self.is_python35 = False
        if sys.version_info.major == 3 and sys.version_info.minor == 5:
            self.is_python35 = True

    def __call__(self, outs_dict, shape_list):
        p_score, p_border, p_direction, p_char = outs_dict[:4]
        p_score = p_score[0].numpy()
        p_border = p_border[0].numpy()
        p_direction = p_direction[0].numpy()
        p_char = p_char[0].numpy()
        src_h, src_w, ratio_h, ratio_w = shape_list[0]
        if self.valid_set != 'totaltext':
            is_curved = False
        else:
            is_curved = True
        instance_yxs_list = generate_pivot_list(
            p_score,
            p_char,
            p_direction,
            score_thresh=self.score_thresh,
            is_backbone=True,
            is_curved=is_curved)
        p_char = np.expand_dims(p_char, axis=0)
        p_char = paddle.to_tensor(p_char)
        char_seq_idx_set = []
        for i in range(len(instance_yxs_list)):
            gather_info_lod = paddle.to_tensor(instance_yxs_list[i])
            f_char_map = paddle.transpose(p_char, [0, 2, 3, 1])
            featyre_seq = paddle.gather_nd(f_char_map, gather_info_lod)
            featyre_seq = np.expand_dims(featyre_seq.numpy(), axis=0)
            t = len(featyre_seq[0])
            featyre_seq = paddle.to_tensor(featyre_seq)
            l = np.array([[t]]).astype(np.int64)
            length = paddle.to_tensor(l)
            seq_pred = paddle.fluid.layers.ctc_greedy_decoder(
                input=featyre_seq, blank=36, input_length=length)
            seq_pred1 = seq_pred[0].numpy().tolist()[0]
            seq_len = seq_pred[1].numpy()[0][0]
            temp_t = []
            for x in seq_pred1[:seq_len]:
                temp_t.append(x)
            char_seq_idx_set.append(temp_t)
        seq_strs = []
        for char_idx_set in char_seq_idx_set:
            pr_str = ''.join([self.Lexicon_Table[pos] for pos in char_idx_set])
            seq_strs.append(pr_str)
        poly_list = []
        keep_str_list = []
        all_point_list = []
        all_point_pair_list = []
        for yx_center_line, keep_str in zip(instance_yxs_list, seq_strs):
            if len(yx_center_line) == 1:
                print('the length of tcl point is less than 2, repeat')
                yx_center_line.append(yx_center_line[-1])

            # expand corresponding offset for total-text.
            offset_expand = 1.0
            if self.valid_set == 'totaltext':
                offset_expand = 1.2

            point_pair_list = []
            for batch_id, y, x in yx_center_line:
                offset = p_border[:, y, x].reshape(2, 2)
                if offset_expand != 1.0:
                    offset_length = np.linalg.norm(
                        offset, axis=1, keepdims=True)
                    expand_length = np.clip(
                        offset_length * (offset_expand - 1),
                        a_min=0.5,
                        a_max=3.0)
                    offset_detal = offset / offset_length * expand_length
                    offset = offset + offset_detal
                ori_yx = np.array([y, x], dtype=np.float32)
                point_pair = (ori_yx + offset)[:, ::-1] * 4.0 / np.array(
                    [ratio_w, ratio_h]).reshape(-1, 2)
                point_pair_list.append(point_pair)

                # for visualization
                all_point_list.append([
                    int(round(x * 4.0 / ratio_w)),
                    int(round(y * 4.0 / ratio_h))
                ])
                all_point_pair_list.append(point_pair.round().astype(np.int32)
                                           .tolist())

            # ndarry: (x, 2)
            detected_poly, pair_length_info = point_pair2poly(point_pair_list)
            print('expand along width. {}'.format(detected_poly.shape))
            detected_poly = expand_poly_along_width(
                detected_poly, shrink_ratio_of_width=0.2)
            detected_poly[:, 0] = np.clip(
                detected_poly[:, 0], a_min=0, a_max=src_w)
            detected_poly[:, 1] = np.clip(
                detected_poly[:, 1], a_min=0, a_max=src_h)

            if len(keep_str) < 2:
                print('--> too short, {}'.format(keep_str))
                continue

            keep_str_list.append(keep_str)
            if self.valid_set == 'partvgg':
                middle_point = len(detected_poly) // 2
                detected_poly = detected_poly[
                    [0, middle_point - 1, middle_point, -1], :]
                poly_list.append(detected_poly)
            elif self.valid_set == 'totaltext':
                poly_list.append(detected_poly)
            else:
                print('--> Not supported format.')
                exit(-1)
        data = {
            'points': poly_list,
            'strs': keep_str_list,
        }
        # visualization
        # if self.save_visualization:
        #     visualize_e2e_result(im_fn, poly_list, keep_str_list, src_im)
        #     visualize_point_result(im_fn, all_point_list, all_point_pair_list, src_im)

        # save detected boxes
        # txt_dir = (result_path[:-1] if result_path.endswith('/') else result_path) + '_txt_anno'
        # if not os.path.exists(txt_dir):
        #     os.makedirs(txt_dir)
        # res_file = os.path.join(txt_dir, '{}.txt'.format(im_prefix))
        # with open(res_file, 'w') as f:
        #     for i_box, box in enumerate(poly_list):
        #         seq_str = keep_str_list[i_box]
        #         box = np.round(box).astype('int32')
        #         box_str = ','.join(str(s) for s in (box.flatten().tolist()))
        #         f.write('{}\t{}\r\n'.format(box_str, seq_str))
        return data
