# blockchain
## 一个区块链原型程序，实现了如下基本功能

-  添加交易信息
-  生成区块
-  注册节点
-  解决冲突
-  工作量证明（POW）
-  验证工作量

## 运行方法
1 python直接运行：
```
python blockchain.py -p 80
python blockchain.py -p 81
```
2 docker 运行：

```
docker build -t blockchain https://github.com/YngwieWang/blockchain.git
docker run -dp 80:5000 blockchain
docker run -dp 81:5000 blockchain
```