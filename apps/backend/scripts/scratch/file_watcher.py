"""文件监视器"""
# from typing import Any
from typing import Callable, Optional
import threading
from pathlib import Path
from app.library.domain.type_profile import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, NOVEL_EXTENSIONS, MODEL_EXTENSIONS, COMIC_EXTENSIONS
from app.library.domain.models import ResourceType
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from calculateSHA256 import calculate_sha256_from_file
from ..log import logger
import os
import time
import queue
# 资源类型对应文件扩展名映射
File_Extension_Map = {
  ResourceType.AUDIO: AUDIO_EXTENSIONS,
  ResourceType.VIDEO: VIDEO_EXTENSIONS,
  ResourceType.IMAGE: IMAGE_EXTENSIONS,
  ResourceType.NOVEL: NOVEL_EXTENSIONS,
  ResourceType.MODEL: MODEL_EXTENSIONS,
  ResourceType.COMIC: COMIC_EXTENSIONS,
}

def file_extension_from_type(type_: ResourceType) -> frozenset[str]:
  return File_Extension_Map[type_]

class FileWatcherHandler(FileSystemEventHandler):
  def __init__(self, queue: queue.Queue):
    self.queue = queue
  """处理文件变化的处理器"""
  def on_created(self,event: FileSystemEvent, async_callback:Optional[Callable] = None):
    logger.info('文件创建: %s', event.src_path)
    self.queue.put(event.src_path)
    
  def on_deleted(self,event: FileSystemEvent, async_callback:Optional[Callable] = None):
    logger.info('文件删除: %s', event.src_path)
    self.queue.put(event.src_path)



  def on_modified(self,event: FileSystemEvent, async_callback:Optional[Callable] = None):
    logger.info('文件修改: %s', event.src_path)
    self.queue.put(event.src_path)



  def on_moved(self,event: FileSystemEvent, async_callback:Optional[Callable] = None):
    logger.info('文件移动: %s', event.src_path)
    self.queue.put(event.src_path)





class FileWatcher():
  def __init__(self, watch_dirs: list[str], callback: Optional[Callable] = None):
    self.watch_dirs = watch_dirs # 监视的目录
    self.queue = queue.Queue() # 队列，用于存放触发了监听的文件路径
    self.handler = FileWatcherHandler(self.queue) # 处理器
    self.observer = Observer() # 观察者
    self._worker = None # 工作线程，用于处理队列中的文件
    self._stop = threading.Event() # 停止事件，用于停止工作线程
    self.callback = callback
    self._processed: dict[str, str] = {}
    """为什么不在on_created这些函数的回调里面处理，而是在工作线程里面处理？
    
    因为on_created这些函数的回调里面处理，会导致阻塞watchdog所在的线程，可能无法及时响应文件变化，影响性能
    而工作线程里面处理，不会阻塞主线程，不会影响性能
    """

  def init_watcher(self):
    watch_dirs: list[str] = []
    for watch_dir in self.watch_dirs:
      watch_dirs.append(str(Path(watch_dir).resolve())) # 将监视的目录转换为绝对路径
    for watch_dir in watch_dirs:
      logger.info(f'监视的目录: {watch_dir}')
      self.observer.schedule(self.handler, watch_dir, recursive=True)
    self.observer.start()
    self._worker = threading.Thread(target=self.run_queue, daemon=True)
    self._worker.start()

  def stop_watcher(self):
    self._stop.set()
    if self._worker:
      self._worker.join(timeout = 5)
    self.observer.stop()
    self.observer.join()
    logger.info("文件监视器已停止")


  def handle(self,file: str):
    if self.wait_until_stable(file):
      # 计算sha256值
      try:
        sha256 = calculate_sha256_from_file(file)
        if self._processed.get(file) == sha256:
          return          # 内容没变，跳过
        self._processed[file] = sha256
        dataList = ['测试hash','测试hash','测试hash',]
        if sha256 in dataList:
          return
        else:
          self.callback(file, sha256)
      except Exception as e:
        print(f"计算sha256失败： {file}, 错误信息: {e}")

  # 处理入队列的文件路径
  """
  注意：需要处理文件夹复制以及重命名的问题，如果是文件夹复制，会监听到文件夹里面的创建事件
  注意：需要计算md5，后续数据库中也要有md5,考虑如何存放
  """
  
  def run_queue(self):
    while not self._stop.is_set():
      try:
        item = self.queue.get()
        self.handle(item)
      except queue.Empty:
        continue
  


def handle(file: str, sha256: str):
  print(f"处理文件: {file}, SHA256: {sha256}")
    



if __name__ == "__main__":
  watch_dirs = [r'D:\Temp']
  watcher = FileWatcher(watch_dirs, callback=handle)
  watcher.init_watcher()
  while True:
    time.sleep(1)