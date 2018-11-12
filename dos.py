'''
_____________________________________________________________________
|[] R3DXPL0IT SHELL                                            |ROOT]|!"|
|"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""|"| 
|CODED BY > R3DXPLOIT(JIMMY)                                          | |
|EMAIL > RETURN_ROOT@PROTONMAIL.COM                                   | |
|GITHUB > https://github.com/r3dxpl0it                                | |
|WEB-PAGE > https://r3dxpl0it.Github.io                               |_|
|_____________________________________________________________________|/|

Test node responses to invalid blocks.
In this test we connect to one node over p2p, and test block requests:
1) Valid blocks should be requested and become chain tip.
2) Invalid block with duplicated transaction should be re-requested.
3) Invalid block with bad coinbase value should be rejected and not
re-requested.
'''
import copy
import struct

from test_framework.blocktools import create_block, create_coinbase, create_tx_with_script, create_transaction, add_witness_commitment, get_witness_script

from test_framework.messages import COIN, hex_str_to_bytes, CTransaction, bytes_to_hex_str, CTxWitness, sha256, CBlock, msg_witness_block, msg_block, CTxInWitness, ser_uint256, CTxOut

from test_framework.mininode import P2PDataStore, NetworkThread, MAGIC_BYTES
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal
from io import BytesIO

class InvalidBlockRequestTest(BitcoinTestFramework):
    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True
        self.extra_args = [["-whitelist=127.0.0.1"], []]

    def run_test(self):
        # Add p2p connection to node0
        node0 = self.nodes[0]  # convenience reference to the node
        node0.add_p2p_connection(P2PDataStore())

        n0_addr = node0.getnewaddress()
        n0_pubk = hex_str_to_bytes(node0.getaddressinfo(n0_addr)["pubkey"])
        
        node1 = self.nodes[1]
        n1_addr = node1.getnewaddress()

        # Generate the first block and let node0 get 50 BTC from the coinbase transaction as the initial funding
        best_block = node0.getblock(node0.getbestblockhash())
        tip = int(node0.getbestblockhash(), 16)
        height = best_block["height"] + 1
        block_time = best_block["time"] + 1
        self.log.info("Create a new block using the coinbase of the node0.")

        block1 = create_block(tip, create_coinbase(height, n0_pubk), block_time)
        block1.solve()
        node0.p2p.send_blocks_and_test([block1], node0, success=True, timeout=60)
        self.log.info("Mature the block, make the mined BTC usable.")
        node0.generatetoaddress(100, node0.get_deterministic_priv_key().address) # generate 100 more blocks.
        assert(node0.getbalance() == 50)   # node0 get the reward as a miner

        # craft a new transaction, which double spend the coinbase tx of node0 in block1
        tx2_raw = node0.createrawtransaction(
            inputs = [{"txid": block1.vtx[0].hash, "vout": 0}, {"txid": block1.vtx[0].hash, "vout": 0}],
            outputs = {n1_addr: 100}
        )

        tx2_sig = node0.signrawtransactionwithwallet(tx2_raw)
        assert_equal(tx2_sig["complete"], True)
        tx2_hex = tx2_sig["hex"]
        tct2 = CTransaction()
        tct2.deserialize(BytesIO(hex_str_to_bytes(tx2_hex)))

        best_block = node0.getblock(node0.getbestblockhash())
        tip = int(node0.getbestblockhash(), 16)
        height = best_block["height"] + 1
        block_time = best_block["time"] + 1
        block2 = create_block(tip, create_coinbase(height), block_time)
        block2.vtx.extend([tct2])
        block2.hashMerkleRoot = block2.calc_merkle_root()
        block2.solve()
        node0.p2p.send_blocks_and_test([block2], node0, success=True, timeout=60)

        # check the balances
        assert(node0.getbalance() == 0)
        assert(node1.getbalance() == 100)
        self.log.info("Successfully double spend the 50 BTCs.")

if __name__ == '__main__':
    InvalidBlockRequestTest().main()
