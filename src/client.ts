import { createClient } from 'genlayer-js'
import { testnetBradbury } from 'genlayer-js/chains'
import { TransactionStatus } from 'genlayer-js/types'
import { getAddress } from 'viem'

// ---- ADDRESS (env first, fallback second — keep both in sync on redeploy) ----
const FALLBACK_ADDRESS = '0xCb91b3A827c5FE73D43A9431FC5a1fbB9cfBfea1'
export const CONTRACT_ADDRESS = ((import.meta as any).env.VITE_CONTRACT_ADDRESS ||
  FALLBACK_ADDRESS) as string

let client: any = null
export let connectedAddress: string | null = null

const CHAIN_ID_HEX = '0x' + testnetBradbury.id.toString(16)

// ---- NETWORK GUARD (runs on connect AND before every write) ----
async function ensureCorrectNetwork(): Promise<void> {
  const eth = (window as any).ethereum
  if (!eth) return
  try {
    await eth.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: CHAIN_ID_HEX }]
    })
  } catch (err: any) {
    if (err && (err.code === 4902 || (err.data && err.data.originalError && err.data.originalError.code === 4902))) {
      await eth.request({
        method: 'wallet_addEthereumChain',
        params: [{
          chainId: CHAIN_ID_HEX,
          chainName: testnetBradbury.name,
          rpcUrls: testnetBradbury.rpcUrls.default.http,
          nativeCurrency: testnetBradbury.nativeCurrency
        }]
      })
      await eth.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: CHAIN_ID_HEX }]
      })
    } else {
      throw err
    }
  }
}

// ---- CONNECTION ----
export async function connectWallet(): Promise<string> {
  const eth = (window as any).ethereum
  if (!eth) throw new Error('No wallet found. Please install Rabby or MetaMask.')
  const accounts: string[] = await eth.request({ method: 'eth_requestAccounts' })
  // Normalize to EIP-55 checksummed form — the contract stores member keys
  // checksummed, and TreeMap string keys are case-sensitive.
  connectedAddress = getAddress(accounts[0])
  await ensureCorrectNetwork()
  client = createClient({ chain: testnetBradbury, account: connectedAddress as any })
  return connectedAddress
}

function getReadClient(): any {
  if (client) return client
  return createClient({ chain: testnetBradbury })
}

// ---- CORE READ / WRITE ----
export async function readContract(functionName: string, args: any[] = []): Promise<any> {
  const c = getReadClient()
  return await c.readContract({
    address: CONTRACT_ADDRESS as any,
    functionName,
    args: args as any[]
  })
}

export async function writeContract(functionName: string, args: any[] = []): Promise<any> {
  if (!client || !connectedAddress) throw new Error('Connect your wallet first.')
  await ensureCorrectNetwork()
  const hash = await client.writeContract({
    address: CONTRACT_ADDRESS as any,
    functionName,
    args: args as any[],
    value: 0n
  })
  const receipt = await (client as any).waitForTransactionReceipt({
    hash,
    status: TransactionStatus.FINALIZED,
    retries: 200,
    interval: 5000
  })
  return receipt
}

// ---- FROZEN INTERFACE: WRITES ----
export const joinDao = () => writeContract('join_dao')
export const createProposal = (
  title: string, summary: string, projectUrl: string,
  budget: number, milestonesJson: string
) => writeContract('create_proposal', [title, summary, projectUrl, budget, milestonesJson])
export const screenProposal = (proposalId: string) => writeContract('screen_proposal', [proposalId])
export const voteOnProposal = (proposalId: string, support: boolean) => writeContract('vote', [proposalId, support])
export const finalizeVote = (proposalId: string) => writeContract('finalize_vote', [proposalId])
export const submitEvidence = (proposalId: string, milestoneIndex: number, evidenceUrl: string) =>
  writeContract('submit_evidence', [proposalId, milestoneIndex, evidenceUrl])
export const verifyMilestone = (proposalId: string, milestoneIndex: number) =>
  writeContract('verify_milestone', [proposalId, milestoneIndex])

// ---- FROZEN INTERFACE: VIEWS (contract returns JSON strings) ----
async function readJson(functionName: string, args: any[] = []): Promise<any> {
  const raw = await readContract(functionName, args)
  if (typeof raw === 'string') {
    try { return JSON.parse(raw) } catch { return null }
  }
  return raw
}

export const getStats = () => readJson('get_stats')
export const getAllProposals = () => readJson('get_all_proposals')
export const getProposal = (proposalId: string) => readJson('get_proposal', [proposalId])
export const getMember = (address: string) => {
  let normalized = address
  try { normalized = getAddress(address) } catch { /* leave as-is */ }
  return readJson('get_member', [normalized])
}
