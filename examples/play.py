from aep import AEP

# 初始化 AEP，如果目录不存在会自动创建 basic 结构
aep = AEP("./my_agent_workspace")

# 1. 查看环境内容
files = aep.ls("/library")
print(f"目录内容: {files}")

# 2. 读取文件内容 (支持行数过滤)
content = aep.cat("library/readme.md", start_line=1, end_line=100)
print(content)
# 3. 全文搜索
matches = aep.grep("aep", path="/")
print(matches)
