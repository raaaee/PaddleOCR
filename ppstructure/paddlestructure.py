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
import logging
import os
import sys

__dir__ = os.path.dirname(__file__)
sys.path.append(os.path.join(__dir__, ''))


import cv2
import numpy as np
from pathlib import Path

from ppocr.utils.logging import get_logger
from predict_system import OCRSystem, save_res
from utility import init_args

logger = get_logger()
from ppocr.utils.utility import check_and_read_gif, get_image_file_list
from ppocr.utils.network import maybe_download, download_with_progressbar

__all__ = ['PaddleStructure']

VERSION = '2.1'
BASE_DIR = os.path.expanduser("~/.paddlestructure/")

model_urls = {
    'det': {
        'https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_det_infer.tar',
    },
    'rec': {
        'https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_det_infer.tar',
    },
    'structure': {
        'https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_det_infer.tar',
    },
}


def parse_args(mMain=True):
    import argparse
    parser = init_args()
    parser.add_help = mMain

    for action in parser._actions:
        if action.dest in ['rec_char_dict_path', 'structure_char_dict_path']:
            action.default = None
    if mMain:
        return parser.parse_args()
    else:
        inference_args_dict = {}
        for action in parser._actions:
            inference_args_dict[action.dest] = action.default
        return argparse.Namespace(**inference_args_dict)


class PaddleStructure(OCRSystem):
    def __init__(self, **kwargs):
        params = parse_args(mMain=False)
        params.__dict__.update(**kwargs)
        if params.show_log:
            logger.setLevel(logging.DEBUG)
        params.use_angle_cls = False
        # init model dir
        if params.det_model_dir is None:
            params.det_model_dir = os.path.join(BASE_DIR, VERSION, 'det')
        if params.rec_model_dir is None:
            params.rec_model_dir = os.path.join(BASE_DIR, VERSION, 'rec')
        if params.structure_model_dir is None:
            params.structure_model_dir = os.path.join(BASE_DIR, VERSION, 'structure')
        # download model
        maybe_download(params.det_model_dir, model_urls['det'])
        maybe_download(params.det_model_dir, model_urls['rec'])
        maybe_download(params.det_model_dir, model_urls['structure'])

        if params.rec_char_dict_path is None:
            params.rec_char_type = 'EN'
            if os.path.exists(str(Path(__file__).parent / 'ppocr/utils/dict/table_dict.txt')):
                params.rec_char_dict_path = str(Path(__file__).parent / 'ppocr/utils/dict/table_dict.txt')
            else:
                params.rec_char_dict_path = str(Path(__file__).parent.parent / 'ppocr/utils/dict/table_dict.txt')
        if params.structure_char_dict_path is None:
            if os.path.exists(str(Path(__file__).parent / 'ppocr/utils/dict/table_structure_dict.txt')):
                params.structure_char_dict_path = str(Path(__file__).parent / 'ppocr/utils/dict/table_structure_dict.txt')
            else:
                params.structure_char_dict_path = str(Path(__file__).parent.parent / 'ppocr/utils/dict/table_structure_dict.txt')

        print(params)
        super().__init__(params)

    def __call__(self, img):
        if isinstance(img, str):
            # download net image
            if img.startswith('http'):
                download_with_progressbar(img, 'tmp.jpg')
                img = 'tmp.jpg'
            image_file = img
            img, flag = check_and_read_gif(image_file)
            if not flag:
                with open(image_file, 'rb') as f:
                    np_arr = np.frombuffer(f.read(), dtype=np.uint8)
                    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                logger.error("error in loading image:{}".format(image_file))
                return None
        if isinstance(img, np.ndarray) and len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        res = super().__call__(img)
        return res


def main():
    # for cmd
    args = parse_args(mMain=True)
    image_dir = args.image_dir
    save_folder = args.output
    if image_dir.startswith('http'):
        download_with_progressbar(image_dir, 'tmp.jpg')
        image_file_list = ['tmp.jpg']
    else:
        image_file_list = get_image_file_list(args.image_dir)
    if len(image_file_list) == 0:
        logger.error('no images find in {}'.format(args.image_dir))
        return

    structure_engine = PaddleStructure(**(args.__dict__))
    for img_path in image_file_list:
        img_name = os.path.basename(img_path).split('.')[0]
        logger.info('{}{}{}'.format('*' * 10, img_path, '*' * 10))
        result = structure_engine(img_path)
        save_res(result, args.output, os.path.basename(img_path).split('.')[0])
        for item in result:
            logger.info(item['res'])
        save_res(result, save_folder, img_name)
        logger.info('result save to {}'.format(os.path.join(save_folder, img_name)))



if __name__ == '__main__':
    table_engine = PaddleStructure(det_model_dir='../inference/table/ch_ppocr_mobile_v2.0_table_det_infer',
                                   rec_model_dir='../inference/table/ch_ppocr_mobile_v2.0_table_rec_infer',
                                   structure_model_dir='../inference/table/ch_ppocr_mobile_v2.0_table_structure_infer',
                                   output='/Users/zhoujun20/Desktop/工作相关/table/table_pr/PaddleOCR/output/table',
                                   show_log=True)
    img = cv2.imread('/Users/zhoujun20/Desktop/工作相关/table/table_pr/PaddleOCR/ppstructure/test_imgs/table_1.png')
    result = table_engine(img)
    for line in result:
        print(line)
