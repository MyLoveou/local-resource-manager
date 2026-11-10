import hashlib
import os

# 计算文件的md5值
def calculate_md5_from_file(file_path: str)-> str:
  try:
    with open(file_path, 'rb') as f:
      md5_hash = hashlib.md5()
      for byte_block in iter(lambda: f.read(4096), b""):
        md5_hash.update(byte_block)
    return md5_hash.hexdigest()
  except Exception as e:
    print(f"Error occurred while calculating MD5: {e}")
    return None

"""
注意：md5算法在安全性方面已经被认为是不够安全的，容易受到碰撞攻击。因此，在需要高安全性的场景下，建议使用更安全的哈希算法，如SHA-256或SHA-3。
"""