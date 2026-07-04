<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { store, navigate } from '../store'
import { getMember, joinDao, createProposal } from '../client'

const member = ref<any>(null)
const checking = ref(false)
const busy = ref('')
const txnote = ref('')

// --- proposal form state ---
const title = ref('')
const summary = ref('')
const projectUrl = ref('')
const budget = ref<number | null>(null)
const milestones = ref([
  { title: '', deliverable: '' },
  { title: '', deliverable: '' }
])

const isMember = computed(() => !!member.value?.joined)
const canAddMilestone = computed(() => milestones.value.length < 4)
const canRemoveMilestone = computed(() => milestones.value.length > 2)
const formValid = computed(() =>
  title.value.trim() && summary.value.trim() && projectUrl.value.trim() &&
  budget.value && budget.value > 0 &&
  milestones.value.every(m => m.title.trim() && m.deliverable.trim())
)

async function loadMember() {
  if (!store.wallet) { member.value = null; return }
  checking.value = true
  try { member.value = await getMember(store.wallet) } catch { member.value = null }
  checking.value = false
}
onMounted(loadMember)

async function doJoin() {
  busy.value = 'join'
  txnote.value = 'Joining the assembly — a simple write, usually 30–60 seconds.'
  try {
    await joinDao()
    txnote.value = 'Welcome to the assembly.'
    await loadMember()
  } catch (e: any) {
    txnote.value = 'Failed: ' + (e?.message || 'unknown error') + ' — is your wallet connected?'
  }
  busy.value = ''
}

function addMilestone() { if (canAddMilestone.value) milestones.value.push({ title: '', deliverable: '' }) }
function removeMilestone(i: number) { if (canRemoveMilestone.value) milestones.value.splice(i, 1) }

async function doSubmit() {
  if (!formValid.value) { txnote.value = 'Fill every field — the deliverables are what the AI will verify against, word for word.'; return }
  busy.value = 'submit'
  txnote.value = 'Submitting your proposal to the chain — usually 30–60 seconds.'
  try {
    await createProposal(
      title.value.trim(), summary.value.trim(), projectUrl.value.trim(),
      Number(budget.value), JSON.stringify(milestones.value.map(m => ({ title: m.title.trim(), deliverable: m.deliverable.trim() })))
    )
    txnote.value = 'Proposal is on the floor. Redirecting...'
    setTimeout(() => navigate('proposals'), 1200)
  } catch (e: any) {
    txnote.value = 'Failed: ' + (e?.message || 'unknown error')
  }
  busy.value = ''
}
</script>

<template>
  <div class="container pagepad">
    <div class="eyebrow">Your standing</div>
    <h1 class="pagetitle">Profile</h1>

    <div class="card section" v-if="!store.wallet">
      <div class="note sans">Connect your wallet (top right) to join the assembly and make proposals.</div>
    </div>

    <template v-else>
      <!-- MEMBERSHIP / REPUTATION -->
      <div class="card section">
        <div v-if="checking" class="note sans">Checking your standing...</div>
        <template v-else-if="isMember">
          <div class="repgrid sans">
            <div class="rep"><div class="replabel">Reputation</div><div class="repvalue bz">{{ member?.reputation ?? 0 }}</div></div>
            <div class="rep"><div class="replabel">Proposals submitted</div><div class="repvalue">{{ member?.submitted ?? 0 }}</div></div>
            <div class="rep"><div class="replabel">Projects completed</div><div class="repvalue">{{ member?.completed ?? 0 }}</div></div>
          </div>
        </template>
        <template v-else>
          <div class="note sans">You are not yet a member of the assembly. Membership is open — one wallet, one voice.</div>
          <button class="btn primary actbtn" :disabled="!!busy" @click="doJoin">{{ busy === 'join' ? 'Joining...' : 'Join the assembly' }}</button>
        </template>
      </div>

      <!-- PROPOSAL FORM -->
      <div class="card section" v-if="isMember">
        <div class="eyebrow">Address the assembly</div>
        <div class="formgrid">
          <input v-model="title" placeholder="Project title" />
          <textarea v-model="summary" rows="3" placeholder="Summary — what are you building and why it matters"></textarea>
          <input v-model="projectUrl" placeholder="Project link (GitHub verifies most reliably)" />
          <input v-model.number="budget" type="number" min="1" placeholder="Budget requested (GEN)" />
        </div>

        <div class="msection">
          <div class="mhead sans">Milestones ({{ milestones.length }}/4) — each deliverable is the exact text the AI will verify against</div>
          <div class="mform" v-for="(m, i) in milestones" :key="i">
            <div class="mformtop sans"><span>Milestone {{ i + 1 }}</span>
              <a v-if="canRemoveMilestone" class="mremove" @click="removeMilestone(i)">remove</a></div>
            <input v-model="m.title" placeholder="Short title, e.g. Deploy contract" />
            <textarea v-model="m.deliverable" rows="2" placeholder="Verifiable deliverable, e.g. Public GitHub repo with a README and a contract address on the explorer"></textarea>
          </div>
          <button class="btn ghost smallbtn" v-if="canAddMilestone" @click="addMilestone">+ Add milestone</button>
        </div>

        <button class="btn primary actbtn" :disabled="!!busy || !formValid" @click="doSubmit">{{ busy === 'submit' ? 'Submitting...' : 'Submit proposal' }}</button>
      </div>

      <div class="txnote sans" v-if="txnote">{{ txnote }}</div>
    </template>
  </div>
</template>

<style scoped>
.pagetitle{font-weight:normal;font-size:40px;margin-bottom:30px}
.section{margin-top:22px}
.note{color:var(--ink2);font-size:13.5px;line-height:1.7}
.actbtn{margin-top:18px}
.smallbtn{padding:9px 18px;font-size:11px;margin-top:4px}
.repgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.replabel{font-size:10px;letter-spacing:2px;color:var(--ink2);text-transform:uppercase}
.repvalue{font-size:30px;margin-top:8px;color:var(--ink)}
.repvalue.bz{color:var(--bronze-hi)}
.formgrid{display:flex;flex-direction:column;gap:12px;margin-bottom:24px}
.msection{margin-bottom:8px}
.mhead{font-size:11px;letter-spacing:1px;color:var(--bronze-hi);margin-bottom:14px;line-height:1.6}
.mform{border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:12px;display:flex;flex-direction:column;gap:10px;background:var(--card2)}
.mformtop{display:flex;justify-content:space-between;font-size:11px;letter-spacing:1px;color:var(--ink2)}
.mremove{color:var(--bad, #E24B4A);cursor:pointer;font-size:10px;letter-spacing:1px}
.txnote{margin-top:20px;padding:14px 16px;background:var(--bronze-soft);border:1px solid var(--bronze);border-radius:10px;font-size:12.5px;color:var(--ink);line-height:1.7}
@media(max-width:700px){.repgrid{grid-template-columns:1fr}}
</style>
