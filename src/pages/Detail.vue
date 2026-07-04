<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { store, navigate } from '../store'
import { getProposal, screenProposal, voteOnProposal, finalizeVote, submitEvidence, verifyMilestone } from '../client'

const loading = ref(true)
const p = ref<any>(null)
const busy = ref('')            // which action is in flight
const txnote = ref('')          // status line under action buttons
const evidenceUrl = ref('')

const status = computed(() => (p.value?.status || '').toUpperCase())
const diligence = computed(() => p.value?.diligence || null)
const milestones = computed(() => Array.isArray(p.value?.milestones) ? p.value.milestones : [])
const activeIndex = computed(() => milestones.value.findIndex((m: any) => {
  const s = (m.status || '').toUpperCase()
  return s === 'ACTIVE' || s === 'PENDING_REVIEW' || s === 'FAILED'
}))

async function load() {
  loading.value = true
  try { p.value = await getProposal(store.selectedId) } catch { p.value = null }
  loading.value = false
}
onMounted(load)

async function run(name: string, fn: () => Promise<any>, note: string) {
  busy.value = name
  txnote.value = note + ' — this is an on-chain AI transaction, it can take 1–3 minutes (sometimes longer on a congested testnet). Do not re-click.'
  try {
    await fn()
    txnote.value = 'Finalized. Refreshing...'
    await load()
    txnote.value = ''
  } catch (e: any) {
    txnote.value = 'Failed or timed out: ' + (e?.message || 'unknown error') + ' — a retry usually works.'
  }
  busy.value = ''
}

const doScreen = () => run('screen', () => screenProposal(store.selectedId), 'Screening proposal')
const doVoteYes = () => run('voteyes', () => voteOnProposal(store.selectedId, true), 'Casting YES vote')
const doVoteNo = () => run('voteno', () => voteOnProposal(store.selectedId, false), 'Casting NO vote')
const doFinalize = () => run('finalize', () => finalizeVote(store.selectedId), 'Finalizing vote')
const doSubmitEvidence = (i: number) => {
  if (!evidenceUrl.value.trim()) { txnote.value = 'Paste an evidence URL first (GitHub or live app links verify most reliably).'; return }
  run('evidence', () => submitEvidence(store.selectedId, i, evidenceUrl.value.trim()), 'Submitting evidence')
}
const doVerify = (i: number) => run('verify', () => verifyMilestone(store.selectedId, i), 'Verifying milestone through consensus')

function mdot(m: any): string {
  const s = (m.status || '').toUpperCase()
  if (s === 'PASSED') return 'done'
  if (s === 'ACTIVE' || s === 'PENDING_REVIEW' || s === 'FAILED') return 'active'
  return ''
}
function mstatustext(m: any): string {
  const s = (m.status || '').toUpperCase()
  if (s === 'PASSED') return 'verified'
  if (s === 'PENDING_REVIEW') return 'under review'
  if (s === 'FAILED') return 'failed — resubmit'
  if (s === 'ACTIVE') return 'active'
  return 'locked'
}
</script>

<template>
  <div class="container pagepad">
    <a class="back sans" @click="navigate('proposals')">← All proposals</a>

    <div v-if="loading" class="card note sans">Reading the chain...</div>
    <div v-else-if="!p" class="card note sans">Proposal not found. It may still be finalizing — try again in a minute.</div>

    <template v-else>
      <div class="eyebrow">Proposal #{{ p.id }} · {{ status }}</div>
      <h1 class="pagetitle">{{ p.title }}</h1>
      <div class="meta sans">by {{ p.proposer }} · {{ p.budget }} GEN requested</div>
      <p class="summary sans">{{ p.summary }}</p>
      <a class="plink sans" :href="p.project_url" target="_blank" rel="noopener">{{ p.project_url }}</a>

      <!-- AI DILIGENCE -->
      <div class="card section">
        <div class="eyebrow">The screening</div>
        <template v-if="diligence && diligence.score !== undefined">
          <div class="score"><span class="scorenum">{{ diligence.score }}</span><span class="scoreof sans">/10 feasibility</span>
            <span class="badge" :class="diligence.recommendation === 'FUND' ? 'green' : 'red'">{{ diligence.recommendation }}</span></div>
          <div class="dilblock" v-if="diligence.strengths"><div class="dillabel sans">Strengths</div><div class="diltext sans">{{ diligence.strengths }}</div></div>
          <div class="dilblock" v-if="diligence.risks"><div class="dillabel sans">Risk flags</div><div class="diltext sans">{{ diligence.risks }}</div></div>
        </template>
        <template v-else>
          <div class="note sans">Not screened yet. Anyone may trigger the screening — the contract will read the project link and file its report permanently.</div>
          <button class="btn primary actbtn" :disabled="!!busy" @click="doScreen">{{ busy === 'screen' ? 'Screening...' : 'Run AI screening' }}</button>
        </template>
      </div>

      <!-- VOTING -->
      <div class="card section" v-if="status === 'SCREENED' || status === 'SUBMITTED'">
        <div class="eyebrow">The vote</div>
        <div class="tally sans"><b>{{ p.votes_yes || 0 }}</b> yes · <b>{{ p.votes_no || 0 }}</b> no</div>
        <div class="votebtns">
          <button class="btn primary actbtn" :disabled="!!busy || status !== 'SCREENED'" @click="doVoteYes">{{ busy === 'voteyes' ? 'Casting...' : 'Vote YES' }}</button>
          <button class="btn ghost actbtn" :disabled="!!busy || status !== 'SCREENED'" @click="doVoteNo">{{ busy === 'voteno' ? 'Casting...' : 'Vote NO' }}</button>
          <button class="btn ghost actbtn" :disabled="!!busy || status !== 'SCREENED'" @click="doFinalize">{{ busy === 'finalize' ? 'Finalizing...' : 'Finalize (quorum)' }}</button>
        </div>
        <div class="note sans" v-if="status === 'SUBMITTED'">Voting opens after screening.</div>
      </div>

      <!-- MILESTONES -->
      <div class="card section" v-if="milestones.length">
        <div class="eyebrow">Milestones &amp; tranches</div>
        <div class="mile" v-for="(m, i) in milestones" :key="i">
          <div class="milerow">
            <span class="mdot" :class="mdot(m)"></span>
            <div class="milemain">
              <div class="miletitle">{{ m.title }} <span class="mstatus sans">— {{ mstatustext(m) }}</span></div>
              <div class="miledeliv sans">{{ m.deliverable }}</div>
              <div class="miletranche sans">{{ m.tranche }} GEN tranche</div>
              <div class="verdict sans" v-if="m.verdict_reason">Verdict: {{ m.verdict_reason }}</div>

              <template v-if="status === 'APPROVED' && i === activeIndex">
                <div class="evidencebox" v-if="(m.status || '').toUpperCase() === 'ACTIVE' || (m.status || '').toUpperCase() === 'FAILED'">
                  <input v-model="evidenceUrl" placeholder="Evidence URL — GitHub repo or live app link" />
                  <button class="btn primary actbtn" :disabled="!!busy" @click="doSubmitEvidence(i)">{{ busy === 'evidence' ? 'Submitting...' : 'Submit evidence' }}</button>
                </div>
                <button v-if="(m.status || '').toUpperCase() === 'PENDING_REVIEW'" class="btn primary actbtn" :disabled="!!busy" @click="doVerify(i)">{{ busy === 'verify' ? 'Consensus running...' : 'Verify milestone' }}</button>
              </template>
            </div>
          </div>
        </div>
      </div>

      <div class="txnote sans" v-if="txnote">{{ txnote }}</div>
    </template>
  </div>
</template>

<style scoped>
.back{color:var(--ink2);font-size:12px;letter-spacing:1px;cursor:pointer;display:inline-block;margin-bottom:26px}
.back:hover{color:var(--bronze-hi)}
.pagetitle{font-weight:normal;font-size:36px;margin-bottom:10px}
.meta{font-size:11.5px;color:var(--ink2);letter-spacing:.5px;margin-bottom:18px}
.summary{font-size:14.5px;color:var(--ink);line-height:1.8;max-width:640px;margin-bottom:10px}
.plink{font-size:12px;color:var(--bronze-hi);word-break:break-all}
.section{margin-top:26px}
.note{color:var(--ink2);font-size:13px;line-height:1.7}
.actbtn{margin-top:16px}
.score{display:flex;align-items:baseline;gap:10px;margin-bottom:18px}
.scorenum{font-size:44px;color:var(--bronze-hi)}
.scoreof{font-size:12px;color:var(--ink2)}
.score .badge{margin-left:auto}
.dilblock{margin-bottom:14px}
.dillabel{font-size:10px;letter-spacing:2px;color:var(--bronze-hi);text-transform:uppercase;margin-bottom:5px}
.diltext{font-size:13px;color:var(--ink);line-height:1.7}
.tally{font-size:15px;color:var(--ink);margin-bottom:6px}
.tally b{color:var(--bronze-hi)}
.votebtns{display:flex;gap:10px;flex-wrap:wrap}
.mile{border-bottom:1px solid var(--line);padding:16px 0}
.mile:last-child{border-bottom:none}
.milerow{display:flex;gap:14px;align-items:flex-start}
.mdot{width:11px;height:11px;border-radius:50%;border:1px solid var(--line);background:var(--card2);margin-top:6px;flex-shrink:0}
.mdot.done{background:var(--bronze);border-color:var(--bronze)}
.mdot.active{border-color:var(--bronze-hi)}
.milemain{flex:1}
.miletitle{font-size:16px;margin-bottom:4px}
.mstatus{font-size:11px;color:var(--ink2);letter-spacing:1px}
.miledeliv{font-size:12.5px;color:var(--ink2);line-height:1.6;margin-bottom:4px}
.miletranche{font-size:11px;color:var(--bronze-hi);letter-spacing:.5px}
.verdict{font-size:12px;color:var(--ink2);margin-top:8px;padding:10px;background:var(--card2);border-radius:8px;line-height:1.6}
.evidencebox{margin-top:14px;display:flex;gap:10px;flex-wrap:wrap}
.evidencebox input{flex:1;min-width:240px}
.txnote{margin-top:20px;padding:14px 16px;background:var(--bronze-soft);border:1px solid var(--bronze);border-radius:10px;font-size:12.5px;color:var(--ink);line-height:1.7}
</style>
