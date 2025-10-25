"""
TensorFlow GPU Configuration Helper for DBABandits
Handles GPU compatibility issues with newer compute capabilities
"""

import os
import logging

def configure_tensorflow_gpu(force_cpu=False):
    """
    配置TensorFlow GPU使用
    
    Args:
        force_cpu: 如果为True,强制使用CPU
        
    Returns:
        str: 配置描述
    """
    if force_cpu:
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
        return "TensorFlow configured to use CPU only"
    
    # 尝试配置GPU
    try:
        import tensorflow as tf
        
        # 检测GPU
        gpus = tf.config.list_physical_devices('GPU')
        
        if not gpus:
            return "No GPU detected, using CPU"
        
        # 配置GPU内存增长(避免占用所有GPU内存)
        for gpu in gpus:
            try:
                tf.config.experimental.set_memory_growth(gpu, True)
            except RuntimeError as e:
                logging.warning(f"Could not set memory growth for {gpu}: {e}")
        
        # 检查计算能力
        from tensorflow.python.platform import build_info
        cuda_version = build_info.build_info.get('cuda_version', 'unknown')
        
        return f"GPU configured: {len(gpus)} device(s), CUDA version: {cuda_version}"
        
    except Exception as e:
        # 如果配置失败,回退到CPU
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
        logging.warning(f"GPU configuration failed, falling back to CPU: {e}")
        return "GPU configuration failed, using CPU"


def get_tensorflow_device_info():
    """获取TensorFlow设备信息"""
    try:
        import tensorflow as tf
        
        print("\n" + "="*80)
        print("TensorFlow Device Information")
        print("="*80)
        print(f"TensorFlow version: {tf.__version__}")
        print(f"Built with CUDA: {tf.test.is_built_with_cuda()}")
        
        # GPU设备
        gpus = tf.config.list_physical_devices('GPU')
        print(f"\nGPU devices: {len(gpus)}")
        for i, gpu in enumerate(gpus):
            print(f"  [{i}] {gpu}")
        
        # CPU设备  
        cpus = tf.config.list_physical_devices('CPU')
        print(f"\nCPU devices: {len(cpus)}")
        for i, cpu in enumerate(cpus):
            print(f"  [{i}] {cpu}")
        
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"Error getting device info: {e}")


if __name__ == "__main__":
    # 测试配置
    print(configure_tensorflow_gpu(force_cpu=False))
    get_tensorflow_device_info()
