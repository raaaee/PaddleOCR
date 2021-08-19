#!/bin/bash
FILENAME=$1
# MODE be one of ['lite_train_infer' 'whole_infer' 'whole_train_infer', 'infer', 'cpp_infer']
MODE=$2

dataline=$(cat ${FILENAME})

# parser params
IFS=$'\n'
lines=(${dataline})
function func_parser_key(){
    strs=$1
    IFS=":"
    array=(${strs})
    tmp=${array[0]}
    echo ${tmp}
}
function func_parser_value(){
    strs=$1
    IFS=":"
    array=(${strs})
    tmp=${array[1]}
    echo ${tmp}
}
IFS=$'\n'
# The training params
model_name=$(func_parser_value "${lines[1]}")

trainer_list=$(func_parser_value "${lines[14]}")

# MODE be one of ['lite_train_infer' 'whole_infer' 'whole_train_infer']
MODE=$2

if [ ${MODE} = "lite_train_infer" ];then
    # pretrain lite train data
    wget -nc -P  ./pretrain_models/ https://paddle-imagenet-models-name.bj.bcebos.com/dygraph/MobileNetV3_large_x0_5_pretrained.pdparams
    rm -rf ./train_data/icdar2015
    rm -rf ./train_data/ic15_data
    wget -nc -P ./train_data/ https://paddleocr.bj.bcebos.com/dygraph_v2.0/test/icdar2015_lite.tar
    wget -nc -P ./train_data/ https://paddleocr.bj.bcebos.com/dygraph_v2.0/test/ic15_data.tar # todo change to bcebos

    cd ./train_data/ && tar xf icdar2015_lite.tar && tar xf ic15_data.tar
    ln -s ./icdar2015_lite ./icdar2015
    cd ../
elif [ ${MODE} = "whole_train_infer" ];then
    wget -nc -P  ./pretrain_models/ https://paddle-imagenet-models-name.bj.bcebos.com/dygraph/MobileNetV3_large_x0_5_pretrained.pdparams
    rm -rf ./train_data/icdar2015
    rm -rf ./train_data/ic15_data
    wget -nc -P ./train_data/ https://paddleocr.bj.bcebos.com/dygraph_v2.0/test/icdar2015.tar
    wget -nc -P ./train_data/ https://paddleocr.bj.bcebos.com/dygraph_v2.0/test/ic15_data.tar
    cd ./train_data/ && tar xf icdar2015.tar && tar xf ic15_data.tar && cd ../
elif [ ${MODE} = "whole_infer" ];then
    wget -nc -P  ./pretrain_models/ https://paddle-imagenet-models-name.bj.bcebos.com/dygraph/MobileNetV3_large_x0_5_pretrained.pdparams
    rm -rf ./train_data/icdar2015
    rm -rf ./train_data/ic15_data
    wget -nc -P ./train_data/ https://paddleocr.bj.bcebos.com/dygraph_v2.0/test/icdar2015_infer.tar
    wget -nc -P ./train_data/ https://paddleocr.bj.bcebos.com/dygraph_v2.0/test/ic15_data.tar
    cd ./train_data/ && tar xf icdar2015_infer.tar && tar xf ic15_data.tar
    ln -s ./icdar2015_infer ./icdar2015
    cd ../
elif [ ${MODE} = "infer" ] || [ ${MODE} = "cpp_infer" ];then
    if [ ${model_name} = "ocr_det" ]; then
        eval_model_name="ch_ppocr_mobile_v2.0_det_infer"
        rm -rf ./train_data/icdar2015
        wget -nc -P ./inference https://paddleocr.bj.bcebos.com/dygraph_v2.0/test/ch_det_data_50.tar
        wget -nc  -P ./inference https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_det_infer.tar
        cd ./inference && tar xf ${eval_model_name}.tar && tar xf ch_det_data_50.tar && cd ../
    else 
        rm -rf ./train_data/ic15_data
        eval_model_name="ch_ppocr_mobile_v2.0_rec_infer"
        wget -nc -P ./train_data/ https://paddleocr.bj.bcebos.com/dygraph_v2.0/test/ic15_data.tar
        wget -nc  -P ./inference https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_rec_infer.tar
        cd ./inference && tar xf ${eval_model_name}.tar && tar xf ic15_data.tar && cd ../
    fi 
fi

if [ ${MODE} = "cpp_infer" ];then
    ################### build opencv ###################
    cd deploy/cpp_infer
    rm -rf 3.4.7.tar.gz opencv-3.4.7/
    wget https://github.com/opencv/opencv/archive/3.4.7.tar.gz
    tar -xf 3.4.7.tar.gz

    cd opencv-3.4.7/
    install_path=$(pwd)/opencv-3.4.7/opencv3

    rm -rf build
    mkdir build
    cd build

    cmake .. \
        -DCMAKE_INSTALL_PREFIX=${install_path} \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_SHARED_LIBS=OFF \
        -DWITH_IPP=OFF \
        -DBUILD_IPP_IW=OFF \
        -DWITH_LAPACK=OFF \
        -DWITH_EIGEN=OFF \
        -DCMAKE_INSTALL_LIBDIR=lib64 \
        -DWITH_ZLIB=ON \
        -DBUILD_ZLIB=ON \
        -DWITH_JPEG=ON \
        -DBUILD_JPEG=ON \
        -DWITH_PNG=ON \
        -DBUILD_PNG=ON \
        -DWITH_TIFF=ON \
        -DBUILD_TIFF=ON

    make -j
    make install
    cd ../
    ################### build opencv finished ###################


#     ################### build paddle inference ###################
#     rm -rf Paddle
#     git clone https://github.com/PaddlePaddle/Paddle.git

#     cd Paddle
#     rm -rf build
#     mkdir build
#     cd build

#     cmake  .. \
#         -DWITH_CONTRIB=OFF \
#         -DWITH_MKL=ON \
#         -DWITH_MKLDNN=ON  \
#         -DWITH_TESTING=OFF \
#         -DCMAKE_BUILD_TYPE=Release \
#         -DWITH_INFERENCE_API_TEST=OFF \
#         -DON_INFER=ON \
#         -DWITH_PYTHON=ON
#     make -j
#     make inference_lib_dist
#     cd ../
#     ################### build paddle inference finished ###################


    ################### build PaddleOCR demo ###################
    OPENCV_DIR=$(pwd)/opencv-3.4.7/opencv3/
    LIB_DIR=$(pwd)/Paddle/build/paddle_inference_install_dir/
    CUDA_LIB_DIR=/usr/local/cuda/lib64/
    CUDNN_LIB_DIR=/usr/lib/x86_64-linux-gnu/

    BUILD_DIR=build
    rm -rf ${BUILD_DIR}
    mkdir ${BUILD_DIR}
    cd ${BUILD_DIR}
    cmake .. \
        -DPADDLE_LIB=${LIB_DIR} \
        -DWITH_MKL=ON \
        -DWITH_GPU=OFF \
        -DWITH_STATIC_LIB=OFF \
        -DWITH_TENSORRT=OFF \
        -DOPENCV_DIR=${OPENCV_DIR} \
        -DCUDNN_LIB=${CUDNN_LIB_DIR} \
        -DCUDA_LIB=${CUDA_LIB_DIR} \
        -DTENSORRT_DIR=${TENSORRT_DIR} \

    make -j
    ################### build PaddleOCR demo finished ###################
fi