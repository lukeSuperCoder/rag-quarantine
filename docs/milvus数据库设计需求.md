# milvus数据库设计以及数据写入需求
## 数据库设计
1. 先阅读一下政策法规文档里面的docs文件,根据文档内容看下如何设计chunk比较合适
2. 需要引入相关工具，把DOCS文件转成TXT文件
3. 向量维度DIM，默认按照1536来设计
4. 根据文档内容，看一下是否需要区分多个知识库或文档类型
5. 先使用Milvus Lite方式设计

## 数据写入需求
1. 使用智谱的向量嵌入模型embedding-3,调用方式可以参考‘https://docs.bigmodel.cn/cn/guide/models/embedding/embedding-3’
- 调用示例
```
# 安装最新版本
pip install zai-sdk
# 或指定版本
pip install zai-sdk==0.2.2

# 检查版本
import zai
print(zai.__version__)

# 创建ZhipuAiClient对象
from zai import ZhipuAiClient

client = ZhipuAiClient(api_key="your api key")
response = client.embeddings.create(
    model="embedding-3", #填写需要调用的模型编码
    input=[
        "美食非常美味，服务员也很友好。",
        "这部电影既刺激又令人兴奋。",
        "阅读书籍是扩展知识的好方法。"
    ],
)
print(response)
```
2. 涉及到milvus操作，可以使用 milvus-skills
3. 如果涉及到文本重排序,参考 'https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E6%96%87%E6%9C%AC%E9%87%8D%E6%8E%92%E5%BA%8F'
