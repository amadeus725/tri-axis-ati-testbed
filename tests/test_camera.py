import cv2
import time
import logging

class AdvancedCameraCapture:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.backend = cv2.CAP_DSHOW
        self.cap = None
        
    def initialize_camera(self):
        """初始化摄像头"""
        # 先确保释放之前的实例
        if self.cap:
            self.cap.release()
            time.sleep(1)
            
        # 创建新的实例
        self.cap = cv2.VideoCapture(self.camera_index, self.backend)
        
        if not self.cap.isOpened():
            logging.error("摄像头打开失败")
            return False
            
        # 设置合适的参数
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        
        time.sleep(2)  # 重要：等待摄像头稳定
        return True
    
    def flush_buffer(self, count=5):
        """清空缓冲区"""
        for _ in range(count):
            self.cap.grab()
    
    def capture_frame(self, max_attempts=10):
        """捕获帧"""
        if not self.cap or not self.cap.isOpened():
            if not self.initialize_camera():
                return None
        
        self.flush_buffer(5)  # 清空旧帧
        
        for attempt in range(max_attempts):
            ret, frame = self.cap.read()
            
            if ret and frame is not None and not frame.empty():
                # 验证图像质量
                if frame.mean() > 10 and frame.std() > 10:  # 检查亮度和对比度
                    return frame
                else:
                    logging.warning(f"图像质量不佳 (亮度: {frame.mean()}, 对比度: {frame.std()})")
            
            logging.warning(f"第{attempt+1}次采集失败")
            time.sleep(0.1)
            
            # 每3次失败后重新初始化
            if (attempt + 1) % 3 == 0:
                self.initialize_camera()
        
        return None
    
    def __del__(self):
        if self.cap:
            self.cap.release()

# 使用高级采集器
camera = AdvancedCameraCapture(0)
frame = camera.capture_frame()

if frame is not None:
    cv2.imwrite('final_capture.jpg', frame)
    print("✅ 最终采集成功")
else:
    print("❌ 所有方法都失败，建议:")
    print("1. 检查摄像头硬件连接")
    print("2. 更新摄像头驱动程序")
    print("3. 尝试其他USB端口")
    print("4. 关闭其他使用摄像头的应用程序")