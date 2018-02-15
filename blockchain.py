# -*- coding: UTF-8 -*-

import hashlib
import json
from time import time
from uuid import uuid4
import requests
from flask import Flask, jsonify, request
from urllib.parse import urlparse


class BlockChain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        #  创建创世块
        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        """
        生成一个新块，添加进链
        :param proof: <int> 工作量算法给出的工作量证明
        :param previous_hash: (optional) <str> 前一个块的哈希值
        :return: <dict> 新块
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        #  重置交易列表
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        生成新交易信息，信息将加入到下一个待挖的区块中
        :param sender: <str> 发送者地址
        :param recipient: <str> 接收者地址
        :param amount: <int> 交易额
        :return: <int>记录这笔交易的块的索引
        """

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    def register_node(self, address):
        """
        在节点列表中添加节点
        :param address: <str> 节点地址 Eg. 'http://192.168.100.101'
        :return: None
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """
        检验给定的链是否合法
        :param chain: <list> 一个区块链
        :return: <bool>
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            if self.hash(last_block) != block['previous_hash']:
                return False
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1
        return True

    def resolve_conflicts(self):
        """
        共识算法解决冲突
        使用网络中最长的链
        :return: <bool> True如果链被取代，否则为False
        """
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)

        #  抓取并验证网络中所有节点的链
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            print(node)

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                print(length)
                print(chain)
                print(self.valid_chain(chain))
                #  检查链的长度是否更长，链是否合法
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        #  如果发现了新的合法的更长的链就用它替换我的链
        if new_chain:
            self.chain = new_chain
            return True

        return False

    @staticmethod
    def hash(block):
        """
        生成块的SHA-256 哈希值
        :param block: <dict> 块
        :return: <str> 哈希值
        """
        #  确定字典按键排序，保证哈希一致
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @staticmethod
    def proof_of_work(last_proof):
        """
        工作量证明：
         - 查找一个p'使得hash(pp')以4个0开头
         - p是上一个块的proof，p’是当前的proof
        :param last_proof: <int>
        :return: <int>
        """
        proof = 0
        while hashlib.sha256(f'{last_proof}{proof}'.encode()).hexdigest()[:4] != '0000':
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        验证证明：是否hash(last_proof, proof)以4个0开头
        :param last_proof: <int> Previous proof
        :param proof: <int> Current proof
        :return: <bool> True if correct ,False if not
        """
        return hashlib.sha256(f'{last_proof}{proof}'.encode()).hexdigest()[:4] == '0000'

    @property
    def last_block(self):
        return self.chain[-1]


app = Flask(__name__)

node_identifier = str(uuid4()).replace('-', '')

blockchain = BlockChain()


@app.route('/mine', methods=['GET'])
def mine():
    #  计算工作量证明
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    #  给工作量证明的节点提供奖励
    #  发送者为0表示是新发出的币
    blockchain.new_transaction(
        sender=0,
        recipient=node_identifier,
        amount=1,
    )

    #  将新block加入chain
    block = blockchain.new_block(proof)

    response = {
        'message': 'New Block Forged',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    #  检查交易结构要求的数据项齐全
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    #  创建一笔新交易
    index = blockchain.new_transaction(values['sender'], values['recipient'],
                                       values['amount'])
    response = {'message': f'Transaction will be added to Block{index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return 'Error: please supply a valid nodes', 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New node register successfully',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'our chain was replaced',
            'new_chain': blockchain.chain,
        }
    else:
        response = {
            'message': 'our chain is authoritative',
            'chain': blockchain.chain,
        }

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=5000, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port, debug=True)
