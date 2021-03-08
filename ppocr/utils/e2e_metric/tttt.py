from os import listdir
import os, sys
from scipy import io
import numpy as np
from ppocr.utils.e2e_metric.polygon_fast import iod, area_of_intersection, area
from tqdm import tqdm

try:  # python2
    range = xrange
except Exception:
    # python3
    range = range
"""
Input format: y0,x0, ..... yn,xn. Each detection is separated by the end of line token ('\n')'
"""

# if len(sys.argv) != 4:
#     print('\n usage: test.py pred_dir gt_dir savefile')
#     sys.exit()
global_tp = 0
global_fp = 0
global_fn = 0

tr = 0.7
tp = 0.6
fsc_k = 0.8
k = 2


def get_socre(gt_dict, pred_dict):
    # allInputs = listdir(input_dir)
    allInputs = 1
    global_pred_str = []
    global_gt_str = []
    global_sigma = []
    global_tau = []

    def input_reading_mod(pred_dict, input):
        """This helper reads input from txt files"""
        det = []
        n = len(pred_dict)
        for i in range(n):
            points = pred_dict[i]['points']
            text = pred_dict[i]['text']
            # for i in range(len(points)):
            point = ",".join(map(str, points.reshape(-1, )))
            det.append([point, text])
        return det

    def gt_reading_mod(gt_dict, gt_id):
        """This helper reads groundtruths from mat files"""
        # gt_id = gt_id.split('.')[0]
        gt = []
        n = len(gt_dict)
        for i in range(n):
            points = gt_dict[i]['points'].tolist()
            h = len(points)
            text = gt_dict[i]['text']
            xx = [
                np.array(
                    ['x:'], dtype='<U2'), 0, np.array(
                        ['y:'], dtype='<U2'), 0, np.array(
                            ['#'], dtype='<U1'), np.array(
                                ['#'], dtype='<U1')
            ]
            t_x, t_y = [], []
            for j in range(h):
                t_x.append(points[j][0])
                t_y.append(points[j][1])
            xx[1] = np.array([t_x], dtype='int16')
            xx[3] = np.array([t_y], dtype='int16')
            if text != "":
                xx[4] = np.array([text], dtype='U{}'.format(len(text)))
                xx[5] = np.array(['c'], dtype='<U1')
            gt.append(xx)
        return gt

    def detection_filtering(detections, groundtruths, threshold=0.5):
        for gt_id, gt in enumerate(groundtruths):
            print
            "liushanshan gt[1] = {}".format(gt[1])
            print
            "liushanshan gt[2] = {}".format(gt[2])
            print
            "liushanshan gt[3] = {}".format(gt[3])
            print
            "liushanshan gt[4] = {}".format(gt[4])
            print
            "liushanshan gt[5] = {}".format(gt[5])
            if (gt[5] == '#') and (gt[1].shape[1] > 1):
                gt_x = list(map(int, np.squeeze(gt[1])))
                gt_y = list(map(int, np.squeeze(gt[3])))
                for det_id, detection in enumerate(detections):
                    detection_orig = detection
                    detection = [float(x) for x in detection[0].split(',')]
                    # detection = detection.split(',')
                    detection = list(map(int, detection))
                    det_x = detection[0::2]
                    det_y = detection[1::2]
                    det_gt_iou = iod(det_x, det_y, gt_x, gt_y)
                    if det_gt_iou > threshold:
                        detections[det_id] = []

                detections[:] = [item for item in detections if item != []]
        return detections

    def sigma_calculation(det_x, det_y, gt_x, gt_y):
        """
        sigma = inter_area / gt_area
        """
        # print(area_of_intersection(det_x, det_y, gt_x, gt_y))
        return np.round((area_of_intersection(det_x, det_y, gt_x, gt_y) /
                         area(gt_x, gt_y)), 2)

    def tau_calculation(det_x, det_y, gt_x, gt_y):
        """
        tau = inter_area / det_area
        """
        # print "liushanshan det_x {}".format(det_x)
        # print "liushanshan det_y {}".format(det_y)
        # print "liushanshan area {}".format(area(det_x, det_y))
        # print "liushanshan tau = {}".format(np.round((area_of_intersection(det_x, det_y, gt_x, gt_y) / area(det_x, det_y)), 2))
        if area(det_x, det_y) == 0.0:
            return 0
        return np.round((area_of_intersection(det_x, det_y, gt_x, gt_y) /
                         area(det_x, det_y)), 2)

    ##############################Initialization###################################

    ###############################################################################
    single_data = {}
    for input_id in range(allInputs):

        if (input_id != '.DS_Store') and (input_id != 'Pascal_result.txt') and (
                input_id != 'Pascal_result_curved.txt') and (input_id != 'Pascal_result_non_curved.txt') and (
                input_id != 'Deteval_result.txt') and (input_id != 'Deteval_result_curved.txt') \
                and (input_id != 'Deteval_result_non_curved.txt'):
            print(input_id)
            detections = input_reading_mod(pred_dict, input_id)
            # print "liushanshan detections = {}".format(detections)
            groundtruths = gt_reading_mod(gt_dict, input_id)
            detections = detection_filtering(
                detections,
                groundtruths)  # filters detections overlapping with DC area
            dc_id = []
            for i in range(len(groundtruths)):
                if groundtruths[i][5] == '#':
                    dc_id.append(i)
            cnt = 0
            for a in dc_id:
                num = a - cnt
                del groundtruths[num]
                cnt += 1

            local_sigma_table = np.zeros((len(groundtruths), len(detections)))
            local_tau_table = np.zeros((len(groundtruths), len(detections)))
            local_pred_str = {}
            local_gt_str = {}

            for gt_id, gt in enumerate(groundtruths):
                if len(detections) > 0:
                    for det_id, detection in enumerate(detections):
                        detection_orig = detection
                        detection = [float(x) for x in detection[0].split(',')]
                        detection = list(map(int, detection))
                        pred_seq_str = detection_orig[1].strip()
                        det_x = detection[0::2]
                        det_y = detection[1::2]
                        gt_x = list(map(int, np.squeeze(gt[1])))
                        gt_y = list(map(int, np.squeeze(gt[3])))
                        gt_seq_str = str(gt[4].tolist()[0])

                        local_sigma_table[gt_id, det_id] = sigma_calculation(
                            det_x, det_y, gt_x, gt_y)
                        local_tau_table[gt_id, det_id] = tau_calculation(
                            det_x, det_y, gt_x, gt_y)
                        local_pred_str[det_id] = pred_seq_str
                        local_gt_str[gt_id] = gt_seq_str

            global_sigma.append(local_sigma_table)
            global_tau.append(local_tau_table)
            global_pred_str.append(local_pred_str)
            global_gt_str.append(local_gt_str)
            print
            "liushanshan global_pred_str = {}".format(global_pred_str)
            print
            "liushanshan global_gt_str = {}".format(global_gt_str)
    single_data['sigma'] = global_sigma
    single_data['global_tau'] = global_tau
    single_data['global_pred_str'] = global_pred_str
    single_data['global_gt_str'] = global_gt_str
    return single_data


def combine_results(all_data):
    global_sigma, global_tau, global_pred_str, global_gt_str = [], [], [], []
    for data in all_data:
        global_sigma.append(data['sigma'])
        global_tau.append(data['global_tau'])
        global_pred_str.append(data['global_pred_str'])
        global_gt_str.append(data['global_gt_str'])
    global_accumulative_recall = 0
    global_accumulative_precision = 0
    total_num_gt = 0
    total_num_det = 0
    hit_str_count = 0
    hit_count = 0

    def one_to_one(local_sigma_table, local_tau_table,
                   local_accumulative_recall, local_accumulative_precision,
                   global_accumulative_recall, global_accumulative_precision,
                   gt_flag, det_flag, idy):
        hit_str_num = 0
        for gt_id in range(num_gt):
            gt_matching_qualified_sigma_candidates = np.where(
                local_sigma_table[gt_id, :] > tr)
            gt_matching_num_qualified_sigma_candidates = gt_matching_qualified_sigma_candidates[
                0].shape[0]
            gt_matching_qualified_tau_candidates = np.where(
                local_tau_table[gt_id, :] > tp)
            gt_matching_num_qualified_tau_candidates = gt_matching_qualified_tau_candidates[
                0].shape[0]

            det_matching_qualified_sigma_candidates = np.where(
                local_sigma_table[:, gt_matching_qualified_sigma_candidates[0]]
                > tr)
            det_matching_num_qualified_sigma_candidates = det_matching_qualified_sigma_candidates[
                0].shape[0]
            det_matching_qualified_tau_candidates = np.where(
                local_tau_table[:, gt_matching_qualified_tau_candidates[0]] >
                tp)
            det_matching_num_qualified_tau_candidates = det_matching_qualified_tau_candidates[
                0].shape[0]

            if (gt_matching_num_qualified_sigma_candidates == 1) and (gt_matching_num_qualified_tau_candidates == 1) and \
                    (det_matching_num_qualified_sigma_candidates == 1) and (
                    det_matching_num_qualified_tau_candidates == 1):
                global_accumulative_recall = global_accumulative_recall + 1.0
                global_accumulative_precision = global_accumulative_precision + 1.0
                local_accumulative_recall = local_accumulative_recall + 1.0
                local_accumulative_precision = local_accumulative_precision + 1.0

                gt_flag[0, gt_id] = 1
                matched_det_id = np.where(local_sigma_table[gt_id, :] > tr)
                # recg start
                print
                "liushanshan one to one det_id = {}".format(matched_det_id)
                print
                "liushanshan one to one gt_id = {}".format(gt_id)
                gt_str_cur = global_gt_str[idy][gt_id]
                pred_str_cur = global_pred_str[idy][matched_det_id[0].tolist()[
                    0]]
                print
                "liushanshan one to one gt_str_cur = {}".format(gt_str_cur)
                print
                "liushanshan one to one pred_str_cur = {}".format(pred_str_cur)
                if pred_str_cur == gt_str_cur:
                    hit_str_num += 1
                else:
                    if pred_str_cur.lower() == gt_str_cur.lower():
                        hit_str_num += 1
                # recg end
                det_flag[0, matched_det_id] = 1
        return local_accumulative_recall, local_accumulative_precision, global_accumulative_recall, global_accumulative_precision, gt_flag, det_flag, hit_str_num

    def one_to_many(local_sigma_table, local_tau_table,
                    local_accumulative_recall, local_accumulative_precision,
                    global_accumulative_recall, global_accumulative_precision,
                    gt_flag, det_flag, idy):
        hit_str_num = 0
        for gt_id in range(num_gt):
            # skip the following if the groundtruth was matched
            if gt_flag[0, gt_id] > 0:
                continue

            non_zero_in_sigma = np.where(local_sigma_table[gt_id, :] > 0)
            num_non_zero_in_sigma = non_zero_in_sigma[0].shape[0]

            if num_non_zero_in_sigma >= k:
                ####search for all detections that overlaps with this groundtruth
                qualified_tau_candidates = np.where((local_tau_table[
                    gt_id, :] >= tp) & (det_flag[0, :] == 0))
                num_qualified_tau_candidates = qualified_tau_candidates[
                    0].shape[0]

                if num_qualified_tau_candidates == 1:
                    if ((local_tau_table[gt_id, qualified_tau_candidates] >= tp)
                            and
                        (local_sigma_table[gt_id, qualified_tau_candidates] >=
                         tr)):
                        # became an one-to-one case
                        global_accumulative_recall = global_accumulative_recall + 1.0
                        global_accumulative_precision = global_accumulative_precision + 1.0
                        local_accumulative_recall = local_accumulative_recall + 1.0
                        local_accumulative_precision = local_accumulative_precision + 1.0

                        gt_flag[0, gt_id] = 1
                        det_flag[0, qualified_tau_candidates] = 1
                        # recg start
                        print
                        "liushanshan one to many det_id = {}".format(
                            qualified_tau_candidates)
                        print
                        "liushanshan one to many gt_id = {}".format(gt_id)
                        gt_str_cur = global_gt_str[idy][gt_id]
                        pred_str_cur = global_pred_str[idy][
                            qualified_tau_candidates[0].tolist()[0]]
                        print
                        "liushanshan one to many gt_str_cur = {}".format(
                            gt_str_cur)
                        print
                        "liushanshan one to many pred_str_cur = {}".format(
                            pred_str_cur)
                        if pred_str_cur == gt_str_cur:
                            hit_str_num += 1
                        else:
                            if pred_str_cur.lower() == gt_str_cur.lower():
                                hit_str_num += 1
                        # recg end
                elif (np.sum(local_sigma_table[gt_id, qualified_tau_candidates])
                      >= tr):
                    gt_flag[0, gt_id] = 1
                    det_flag[0, qualified_tau_candidates] = 1
                    # recg start
                    print
                    "liushanshan one to many det_id = {}".format(
                        qualified_tau_candidates)
                    print
                    "liushanshan one to many gt_id = {}".format(gt_id)
                    gt_str_cur = global_gt_str[idy][gt_id]
                    pred_str_cur = global_pred_str[idy][
                        qualified_tau_candidates[0].tolist()[0]]
                    print
                    "liushanshan one to many gt_str_cur = {}".format(gt_str_cur)
                    print
                    "liushanshan one to many pred_str_cur = {}".format(
                        pred_str_cur)
                    if pred_str_cur == gt_str_cur:
                        hit_str_num += 1
                    else:
                        if pred_str_cur.lower() == gt_str_cur.lower():
                            hit_str_num += 1
                    # recg end

                    global_accumulative_recall = global_accumulative_recall + fsc_k
                    global_accumulative_precision = global_accumulative_precision + num_qualified_tau_candidates * fsc_k

                    local_accumulative_recall = local_accumulative_recall + fsc_k
                    local_accumulative_precision = local_accumulative_precision + num_qualified_tau_candidates * fsc_k

        return local_accumulative_recall, local_accumulative_precision, global_accumulative_recall, global_accumulative_precision, gt_flag, det_flag, hit_str_num

    def many_to_one(local_sigma_table, local_tau_table,
                    local_accumulative_recall, local_accumulative_precision,
                    global_accumulative_recall, global_accumulative_precision,
                    gt_flag, det_flag, idy):
        hit_str_num = 0
        for det_id in range(num_det):
            # skip the following if the detection was matched
            if det_flag[0, det_id] > 0:
                continue

            non_zero_in_tau = np.where(local_tau_table[:, det_id] > 0)
            num_non_zero_in_tau = non_zero_in_tau[0].shape[0]

            if num_non_zero_in_tau >= k:
                ####search for all detections that overlaps with this groundtruth
                qualified_sigma_candidates = np.where((
                    local_sigma_table[:, det_id] >= tp) & (gt_flag[0, :] == 0))
                num_qualified_sigma_candidates = qualified_sigma_candidates[
                    0].shape[0]

                if num_qualified_sigma_candidates == 1:
                    if ((local_tau_table[qualified_sigma_candidates, det_id] >=
                         tp) and
                        (local_sigma_table[qualified_sigma_candidates, det_id]
                         >= tr)):
                        # became an one-to-one case
                        global_accumulative_recall = global_accumulative_recall + 1.0
                        global_accumulative_precision = global_accumulative_precision + 1.0
                        local_accumulative_recall = local_accumulative_recall + 1.0
                        local_accumulative_precision = local_accumulative_precision + 1.0

                        gt_flag[0, qualified_sigma_candidates] = 1
                        det_flag[0, det_id] = 1
                        # recg start
                        print
                        "liushanshan many to one det_id = {}".format(det_id)
                        print
                        "liushanshan many to one gt_id = {}".format(
                            qualified_sigma_candidates)
                        pred_str_cur = global_pred_str[idy][det_id]
                        gt_len = len(qualified_sigma_candidates[0])
                        for idx in range(gt_len):
                            ele_gt_id = qualified_sigma_candidates[0].tolist()[
                                idx]
                            if not global_gt_str[idy].has_key(ele_gt_id):
                                continue
                            gt_str_cur = global_gt_str[idy][ele_gt_id]
                            print
                            "liushanshan many to one gt_str_cur = {}".format(
                                gt_str_cur)
                            print
                            "liushanshan many to one pred_str_cur = {}".format(
                                pred_str_cur)
                            if pred_str_cur == gt_str_cur:
                                hit_str_num += 1
                                break
                            else:
                                if pred_str_cur.lower() == gt_str_cur.lower():
                                    hit_str_num += 1
                                break
                        # recg end
                elif (np.sum(local_tau_table[qualified_sigma_candidates,
                                             det_id]) >= tp):
                    det_flag[0, det_id] = 1
                    gt_flag[0, qualified_sigma_candidates] = 1
                    # recg start
                    print
                    "liushanshan many to one det_id = {}".format(det_id)
                    print
                    "liushanshan many to one gt_id = {}".format(
                        qualified_sigma_candidates)
                    pred_str_cur = global_pred_str[idy][det_id]
                    gt_len = len(qualified_sigma_candidates[0])
                    for idx in range(gt_len):
                        ele_gt_id = qualified_sigma_candidates[0].tolist()[idx]
                        if not global_gt_str[idy].has_key(ele_gt_id):
                            continue
                        gt_str_cur = global_gt_str[idy][ele_gt_id]
                        print
                        "liushanshan many to one gt_str_cur = {}".format(
                            gt_str_cur)
                        print
                        "liushanshan many to one pred_str_cur = {}".format(
                            pred_str_cur)
                        if pred_str_cur == gt_str_cur:
                            hit_str_num += 1
                            break
                        else:
                            if pred_str_cur.lower() == gt_str_cur.lower():
                                hit_str_num += 1
                                break
                            else:
                                print
                                'no match'
                    # recg end

                    global_accumulative_recall = global_accumulative_recall + num_qualified_sigma_candidates * fsc_k
                    global_accumulative_precision = global_accumulative_precision + fsc_k

                    local_accumulative_recall = local_accumulative_recall + num_qualified_sigma_candidates * fsc_k
                    local_accumulative_precision = local_accumulative_precision + fsc_k
        return local_accumulative_recall, local_accumulative_precision, global_accumulative_recall, global_accumulative_precision, gt_flag, det_flag, hit_str_num

    for idx in range(len(global_sigma)):
        # print(allInputs[idx])
        local_sigma_table = np.array(global_sigma[idx])
        local_tau_table = global_tau[idx]

        num_gt = local_sigma_table.shape[0]
        num_det = local_sigma_table.shape[1]

        total_num_gt = total_num_gt + num_gt
        total_num_det = total_num_det + num_det

        local_accumulative_recall = 0
        local_accumulative_precision = 0
        gt_flag = np.zeros((1, num_gt))
        det_flag = np.zeros((1, num_det))

        #######first check for one-to-one case##########
        local_accumulative_recall, local_accumulative_precision, global_accumulative_recall, global_accumulative_precision, \
        gt_flag, det_flag, hit_str_num = one_to_one(local_sigma_table, local_tau_table,
                                                    local_accumulative_recall, local_accumulative_precision,
                                                    global_accumulative_recall, global_accumulative_precision,
                                                    gt_flag, det_flag, idx)

        hit_str_count += hit_str_num
        #######then check for one-to-many case##########
        local_accumulative_recall, local_accumulative_precision, global_accumulative_recall, global_accumulative_precision, \
        gt_flag, det_flag, hit_str_num = one_to_many(local_sigma_table, local_tau_table,
                                                     local_accumulative_recall, local_accumulative_precision,
                                                     global_accumulative_recall, global_accumulative_precision,
                                                     gt_flag, det_flag, idx)
        hit_str_count += hit_str_num
        #######then check for many-to-one case##########
        local_accumulative_recall, local_accumulative_precision, global_accumulative_recall, global_accumulative_precision, \
        gt_flag, det_flag, hit_str_num = many_to_one(local_sigma_table, local_tau_table,
                                                     local_accumulative_recall, local_accumulative_precision,
                                                     global_accumulative_recall, global_accumulative_precision,
                                                     gt_flag, det_flag, idx)

    try:
        recall = global_accumulative_recall / total_num_gt
    except ZeroDivisionError:
        recall = 0

    try:
        precision = global_accumulative_precision / total_num_det
    except ZeroDivisionError:
        precision = 0

    try:
        f_score = 2 * precision * recall / (precision + recall)
    except ZeroDivisionError:
        f_score = 0

    try:
        seqerr = 1 - float(hit_str_count) / global_accumulative_recall
    except ZeroDivisionError:
        seqerr = 1

    try:
        recall_e2e = float(hit_str_count) / total_num_gt
    except ZeroDivisionError:
        recall_e2e = 0

    try:
        precision_e2e = float(hit_str_count) / total_num_det
    except ZeroDivisionError:
        precision_e2e = 0

    try:
        f_score_e2e = 2 * precision_e2e * recall_e2e / (
            precision_e2e + recall_e2e)
    except ZeroDivisionError:
        f_score_e2e = 0

    final = {
        'total_num_gt': total_num_gt,
        'total_num_det': total_num_det,
        'global_accumulative_recall': global_accumulative_recall,
        'hit_str_count': hit_str_count,
        'recall': recall,
        'precision': precision,
        'f_score': f_score,
        'seqerr': seqerr,
        'recall_e2e': recall_e2e,
        'precision_e2e': precision_e2e,
        'f_score_e2e': f_score_e2e
    }
    return final


# def combine_results(all_data):
#     tr = 0.7
#     tp = 0.6
#     fsc_k = 0.8
#     k = 2
#     global_sigma = []
#     global_tau = []
#     global_pred_str = []
#     global_gt_str = []
#     for data in all_data:
#         global_sigma.append(data['sigma'])
#         global_tau.append(data['global_tau'])
#         global_pred_str.append(data['global_pred_str'])
#         global_gt_str.append(data['global_gt_str'])
#
#     global_accumulative_recall = 0
#     global_accumulative_precision = 0
#     total_num_gt = 0
#     total_num_det = 0
#     hit_str_count = 0
#     hit_count = 0
#
#     def one_to_one(local_sigma_table, local_tau_table, local_accumulative_recall,
#                    local_accumulative_precision, global_accumulative_recall, global_accumulative_precision,
#                    gt_flag, det_flag, idy):
#         hit_str_num = 0
#         for gt_id in range(num_gt):
#             gt_matching_qualified_sigma_candidates = np.where(local_sigma_table[gt_id, :] > tr)
#             gt_matching_num_qualified_sigma_candidates = gt_matching_qualified_sigma_candidates[0].shape[0]
#             gt_matching_qualified_tau_candidates = np.where(local_tau_table[gt_id, :] > tp)
#             gt_matching_num_qualified_tau_candidates = gt_matching_qualified_tau_candidates[0].shape[0]
#
#             det_matching_qualified_sigma_candidates = np.where(
#                 local_sigma_table[:, gt_matching_qualified_sigma_candidates[0]] > tr)
#             det_matching_num_qualified_sigma_candidates = det_matching_qualified_sigma_candidates[0].shape[0]
#             det_matching_qualified_tau_candidates = np.where(
#                 local_tau_table[:, gt_matching_qualified_tau_candidates[0]] > tp)
#             det_matching_num_qualified_tau_candidates = det_matching_qualified_tau_candidates[0].shape[0]
#
#             if (gt_matching_num_qualified_sigma_candidates == 1) and (gt_matching_num_qualified_tau_candidates == 1) and \
#                     (det_matching_num_qualified_sigma_candidates == 1) and (
#                     det_matching_num_qualified_tau_candidates == 1):
#                 global_accumulative_recall = global_accumulative_recall + 1.0
#                 global_accumulative_precision = global_accumulative_precision + 1.0
#                 local_accumulative_recall = local_accumulative_recall + 1.0
#                 local_accumulative_precision = local_accumulative_precision + 1.0
#
#                 gt_flag[0, gt_id] = 1
#                 matched_det_id = np.where(local_sigma_table[gt_id, :] > tr)
#                 # recg start
#                 print
#                 "liushanshan one to one det_id = {}".format(matched_det_id)
#                 print
#                 "liushanshan one to one gt_id = {}".format(gt_id)
#                 gt_str_cur = global_gt_str[idy][gt_id]
#                 pred_str_cur = global_pred_str[idy][matched_det_id[0].tolist()[0]]
#                 print
#                 "liushanshan one to one gt_str_cur = {}".format(gt_str_cur)
#                 print
#                 "liushanshan one to one pred_str_cur = {}".format(pred_str_cur)
#                 if pred_str_cur == gt_str_cur:
#                     hit_str_num += 1
#                 else:
#                     if pred_str_cur.lower() == gt_str_cur.lower():
#                         hit_str_num += 1
#                 # recg end
#                 det_flag[0, matched_det_id] = 1
#         return local_accumulative_recall, local_accumulative_precision, global_accumulative_recall, global_accumulative_precision, gt_flag, det_flag, hit_str_num
#
#     def one_to_many(local_sigma_table, local_tau_table, local_accumulative_recall,
#                     local_accumulative_precision, global_accumulative_recall, global_accumulative_precision,
#                     gt_flag, det_flag, idy):
#         hit_str_num = 0
#         for gt_id in range(num_gt):
#             # skip the following if the groundtruth was matched
#             if gt_flag[0, gt_id] > 0:
#                 continue
#
#             non_zero_in_sigma = np.where(local_sigma_table[gt_id, :] > 0)
#             num_non_zero_in_sigma = non_zero_in_sigma[0].shape[0]
#
#             if num_non_zero_in_sigma >= k:
#                 ####search for all detections that overlaps with this groundtruth
#                 qualified_tau_candidates = np.where((local_tau_table[gt_id, :] >= tp) & (det_flag[0, :] == 0))
#                 num_qualified_tau_candidates = qualified_tau_candidates[0].shape[0]
#
#                 if num_qualified_tau_candidates == 1:
#                     if ((local_tau_table[gt_id, qualified_tau_candidates] >= tp) and (
#                             local_sigma_table[gt_id, qualified_tau_candidates] >= tr)):
#                         # became an one-to-one case
#                         global_accumulative_recall = global_accumulative_recall + 1.0
#                         global_accumulative_precision = global_accumulative_precision + 1.0
#                         local_accumulative_recall = local_accumulative_recall + 1.0
#                         local_accumulative_precision = local_accumulative_precision + 1.0
#
#                         gt_flag[0, gt_id] = 1
#                         det_flag[0, qualified_tau_candidates] = 1
#                         # recg start
#                         print
#                         "liushanshan one to many det_id = {}".format(qualified_tau_candidates)
#                         print
#                         "liushanshan one to many gt_id = {}".format(gt_id)
#                         gt_str_cur = global_gt_str[idy][gt_id]
#                         pred_str_cur = global_pred_str[idy][qualified_tau_candidates[0].tolist()[0]]
#                         print
#                         "liushanshan one to many gt_str_cur = {}".format(gt_str_cur)
#                         print
#                         "liushanshan one to many pred_str_cur = {}".format(pred_str_cur)
#                         if pred_str_cur == gt_str_cur:
#                             hit_str_num += 1
#                         else:
#                             if pred_str_cur.lower() == gt_str_cur.lower():
#                                 hit_str_num += 1
#                         # recg end
#                 elif (np.sum(local_sigma_table[gt_id, qualified_tau_candidates]) >= tr):
#                     gt_flag[0, gt_id] = 1
#                     det_flag[0, qualified_tau_candidates] = 1
#                     # recg start
#                     print
#                     "liushanshan one to many det_id = {}".format(qualified_tau_candidates)
#                     print
#                     "liushanshan one to many gt_id = {}".format(gt_id)
#                     gt_str_cur = global_gt_str[idy][gt_id]
#                     pred_str_cur = global_pred_str[idy][qualified_tau_candidates[0].tolist()[0]]
#                     print
#                     "liushanshan one to many gt_str_cur = {}".format(gt_str_cur)
#                     print
#                     "liushanshan one to many pred_str_cur = {}".format(pred_str_cur)
#                     if pred_str_cur == gt_str_cur:
#                         hit_str_num += 1
#                     else:
#                         if pred_str_cur.lower() == gt_str_cur.lower():
#                             hit_str_num += 1
#                     # recg end
#
#                     global_accumulative_recall = global_accumulative_recall + fsc_k
#                     global_accumulative_precision = global_accumulative_precision + num_qualified_tau_candidates * fsc_k
#
#                     local_accumulative_recall = local_accumulative_recall + fsc_k
#                     local_accumulative_precision = local_accumulative_precision + num_qualified_tau_candidates * fsc_k
#
#         return local_accumulative_recall, local_accumulative_precision, global_accumulative_recall, global_accumulative_precision, gt_flag, det_flag, hit_str_num
#
#     def many_to_one(local_sigma_table, local_tau_table, local_accumulative_recall,
#                     local_accumulative_precision, global_accumulative_recall, global_accumulative_precision,
#                     gt_flag, det_flag, idy):
#         hit_str_num = 0
#         for det_id in range(num_det):
#             # skip the following if the detection was matched
#             if det_flag[0, det_id] > 0:
#                 continue
#
#             non_zero_in_tau = np.where(local_tau_table[:, det_id] > 0)
#             num_non_zero_in_tau = non_zero_in_tau[0].shape[0]
#
#             if num_non_zero_in_tau >= k:
#                 ####search for all detections that overlaps with this groundtruth
#                 qualified_sigma_candidates = np.where((local_sigma_table[:, det_id] >= tp) & (gt_flag[0, :] == 0))
#                 num_qualified_sigma_candidates = qualified_sigma_candidates[0].shape[0]
#
#                 if num_qualified_sigma_candidates == 1:
#                     if ((local_tau_table[qualified_sigma_candidates, det_id] >= tp) and (
#                             local_sigma_table[qualified_sigma_candidates, det_id] >= tr)):
#                         # became an one-to-one case
#                         global_accumulative_recall = global_accumulative_recall + 1.0
#                         global_accumulative_precision = global_accumulative_precision + 1.0
#                         local_accumulative_recall = local_accumulative_recall + 1.0
#                         local_accumulative_precision = local_accumulative_precision + 1.0
#
#                         gt_flag[0, qualified_sigma_candidates] = 1
#                         det_flag[0, det_id] = 1
#                         # recg start
#                         print
#                         "liushanshan many to one det_id = {}".format(det_id)
#                         print
#                         "liushanshan many to one gt_id = {}".format(qualified_sigma_candidates)
#                         pred_str_cur = global_pred_str[idy][det_id]
#                         gt_len = len(qualified_sigma_candidates[0])
#                         for idx in range(gt_len):
#                             ele_gt_id = qualified_sigma_candidates[0].tolist()[idx]
#                             if ele_gt_id not in global_gt_str[idy]:
#                                 continue
#                             gt_str_cur = global_gt_str[idy][ele_gt_id]
#                             print
#                             "liushanshan many to one gt_str_cur = {}".format(gt_str_cur)
#                             print
#                             "liushanshan many to one pred_str_cur = {}".format(pred_str_cur)
#                             if pred_str_cur == gt_str_cur:
#                                 hit_str_num += 1
#                                 break
#                             else:
#                                 if pred_str_cur.lower() == gt_str_cur.lower():
#                                     hit_str_num += 1
#                                 break
#                         # recg end
#                 elif (np.sum(local_tau_table[qualified_sigma_candidates, det_id]) >= tp):
#                     det_flag[0, det_id] = 1
#                     gt_flag[0, qualified_sigma_candidates] = 1
#                     # recg start
#                     print
#                     "liushanshan many to one det_id = {}".format(det_id)
#                     print
#                     "liushanshan many to one gt_id = {}".format(qualified_sigma_candidates)
#                     pred_str_cur = global_pred_str[idy][det_id]
#                     gt_len = len(qualified_sigma_candidates[0])
#                     for idx in range(gt_len):
#                         ele_gt_id = qualified_sigma_candidates[0].tolist()[idx]
#                         if not global_gt_str[idy].has_key(ele_gt_id):
#                             continue
#                         gt_str_cur = global_gt_str[idy][ele_gt_id]
#                         print
#                         "liushanshan many to one gt_str_cur = {}".format(gt_str_cur)
#                         print
#                         "liushanshan many to one pred_str_cur = {}".format(pred_str_cur)
#                         if pred_str_cur == gt_str_cur:
#                             hit_str_num += 1
#                             break
#                         else:
#                             if pred_str_cur.lower() == gt_str_cur.lower():
#                                 hit_str_num += 1
#                                 break
#                             else:
#                                 print
#                                 'no match'
#                     # recg end
#
#                     global_accumulative_recall = global_accumulative_recall + num_qualified_sigma_candidates * fsc_k
#                     global_accumulative_precision = global_accumulative_precision + fsc_k
#
#                     local_accumulative_recall = local_accumulative_recall + num_qualified_sigma_candidates * fsc_k
#                     local_accumulative_precision = local_accumulative_precision + fsc_k
#         return local_accumulative_recall, local_accumulative_precision, global_accumulative_recall, global_accumulative_precision, gt_flag, det_flag, hit_str_num
#
#     for idx in range(len(global_sigma)):
#         local_sigma_table = np.array(global_sigma[idx])
#         local_tau_table = np.array(global_tau[idx])
#
#         num_gt = local_sigma_table.shape[0]
#         num_det = local_sigma_table.shape[1]
#
#         total_num_gt = total_num_gt + num_gt
#         total_num_det = total_num_det + num_det
#
#         local_accumulative_recall = 0
#         local_accumulative_precision = 0
#         gt_flag = np.zeros((1, num_gt))
#         det_flag = np.zeros((1, num_det))
#
#         #######first check for one-to-one case##########
#         local_accumulative_recall, local_accumulative_precision, global_accumulative_recall, global_accumulative_precision, \
#         gt_flag, det_flag, hit_str_num = one_to_one(local_sigma_table, local_tau_table,
#                                                     local_accumulative_recall, local_accumulative_precision,
#                                                     global_accumulative_recall, global_accumulative_precision,
#                                                     gt_flag, det_flag, idx)
#
#         hit_str_count += hit_str_num
#         #######then check for one-to-many case##########
#         local_accumulative_recall, local_accumulative_precision, global_accumulative_recall, global_accumulative_precision, \
#         gt_flag, det_flag, hit_str_num = one_to_many(local_sigma_table, local_tau_table,
#                                                      local_accumulative_recall, local_accumulative_precision,
#                                                      global_accumulative_recall, global_accumulative_precision,
#                                                      gt_flag, det_flag, idx)
#         hit_str_count += hit_str_num
#         #######then check for many-to-one case##########
#         local_accumulative_recall, local_accumulative_precision, global_accumulative_recall, global_accumulative_precision, \
#         gt_flag, det_flag, hit_str_num = many_to_one(local_sigma_table, local_tau_table,
#                                                      local_accumulative_recall, local_accumulative_precision,
#                                                      global_accumulative_recall, global_accumulative_precision,
#                                                      gt_flag, det_flag, idx)
#     try:
#         recall = global_accumulative_recall / total_num_gt
#     except ZeroDivisionError:
#         recall = 0
#
#     try:
#         precision = global_accumulative_precision / total_num_det
#     except ZeroDivisionError:
#         precision = 0
#
#     try:
#         f_score = 2 * precision * recall / (precision + recall)
#     except ZeroDivisionError:
#         f_score = 0
#
#     try:
#         seqerr = 1 - float(hit_str_count) / global_accumulative_recall
#     except ZeroDivisionError:
#         seqerr = 1
#
#     try:
#         recall_e2e = float(hit_str_count) / total_num_gt
#     except ZeroDivisionError:
#         recall_e2e = 0
#
#     try:
#         precision_e2e = float(hit_str_count) / total_num_det
#     except ZeroDivisionError:
#         precision_e2e = 0
#
#     try:
#         f_score_e2e = 2 * precision_e2e * recall_e2e / (precision_e2e + recall_e2e)
#     except ZeroDivisionError:
#         f_score_e2e = 0
#
#     final = {
#         'total_num_gt': total_num_gt,
#         'total_num_det': total_num_det,
#         'global_accumulative_recall': global_accumulative_recall,
#         'hit_str_count': hit_str_count,
#         'recall': recall,
#         'precision': precision,
#         'f_score': f_score,
#         'seqerr': seqerr,
#         'recall_e2e': recall_e2e,
#         'precision_e2e': precision_e2e,
#         'f_score_e2e': f_score_e2e
#     }
#     return final

a = [
    1526, 642, 1565, 629, 1579, 627, 1593, 625, 1607, 623, 1620, 622, 1634, 620,
    1659, 620, 1654, 681, 1631, 680, 1618, 681, 1606, 681, 1594, 681, 1584, 682,
    1573, 685, 1542, 694
]
gt_dict = [{'points': np.array(a).reshape(-1, 2), 'text': 'MILK'}]
pred_dict = [{
    'points': np.array(a),
    'text': 'ccc'
}, {
    'points': np.array(a),
    'text': 'ccf'
}]
result = []
result.append(get_socre(gt_dict, gt_dict))
a = combine_results(result)
print(a)
