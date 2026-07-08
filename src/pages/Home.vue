<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { navigate } from '../store'
import { getStats, getAllProposals } from '../client'
import heroImg from '../assets/hero.jpg'

const words = ['verified', 'trustless', 'earned', 'incorruptible']
const wordIndex = ref(0)
const wordOut = ref(false)
let wordTimer: any = null

const stats = ref({ members: 0, treasury: 0, released: 0, proposals: 0 })
const shown = ref({ members: 0, treasury: 0, released: 0, proposals: 0 })
const featured = ref<any[]>([])
function countUp() {
  const start = performance.now()
  const dur = 1200
  const from = { members: 0, treasury: 0, released: 0, proposals: 0 }
  function tick(now: number) {
    const p = Math.min((now - start) / dur, 1)
    shown.value = {
      members: Math.round(from.members + (stats.value.members - from.members) * p),
      treasury: Math.round(from.treasury + (stats.value.treasury - from.treasury) * p),
      released: Math.round(from.released + (stats.value.released - from.released) * p),
      proposals: Math.round(from.proposals + (stats.value.proposals - from.proposals) * p)
    }
    if (p < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

async function loadChain() {
  try {
    const s = await getStats()
    if (s) stats.value = {
      members: Number(s.members || 0), treasury: Number(s.treasury || 0),
      released: Number(s.released || 0), proposals: Number(s.proposals || 0)
    }
  } catch { /* contract not deployed yet — keep zeros */ }
  countUp()
  try {
    const all = await getAllProposals()
    if (Array.isArray(all)) featured.value = all.slice(-2).reverse()
  } catch { /* quiet floor */ }
}

let io: IntersectionObserver | null = null
onMounted(() => {
  wordTimer = setInterval(() => {
    wordOut.value = true
    setTimeout(() => {
      wordIndex.value = (wordIndex.value + 1) % words.length
      wordOut.value = false
    }, 350)
  }, 2500)
  io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('in'); io?.unobserve(e.target) }
  }), { threshold: 0.15 })
  document.querySelectorAll('.reveal').forEach(el => io?.observe(el))
  loadChain()
})
onUnmounted(() => { clearInterval(wordTimer); io?.disconnect() })

function statusBadge(p: any): { text: string, cls: string } {
  const s = (p.status || '').toUpperCase()
  if (s === 'APPROVED') return { text: 'FUNDED', cls: 'bronze' }
  if (s === 'COMPLETE') return { text: 'COMPLETE', cls: 'green' }
  if (s === 'REJECTED') return { text: 'REJECTED', cls: 'red' }
  if (s === 'SCREENED') return { text: 'VOTING · ' + (p.votes_yes || 0) + 'Y / ' + (p.votes_no || 0) + 'N', cls: 'green' }
  return { text: s || 'SUBMITTED', cls: 'gray' }
}
</script>

<template>
  <header class="hero" :style="{ backgroundImage: 'url(' + heroImg + ')' }">
    <div class="overlay"></div>
    <div class="inner container">
      <div class="wordmark">AGORA<b>GRANTS</b></div>
      <div class="netline sans">Built on <i>GenLayer · Bradbury Testnet</i></div>
      <h2 class="rotline">Funding that is <span class="word" :class="{ out: wordOut }">{{ words[wordIndex] }}</span>.</h2>
      <p class="sub sans">A grant DAO where money moves only when the work is real. AI screens every proposal, members cast the votes, and the contract itself inspects each milestone before a single token is released.</p>
      <button class="btn primary" @click="navigate('profile')">Join the assembly</button>
      <button class="btn ghost heroghost" @click="navigate('proposals')">See the proposals</button>
    </div>
  </header>

  <main class="container">
    <div class="stats reveal">
      <div class="stat sans"><div class="label">Members</div><div class="value">{{ shown.members }}</div></div>
      <div class="stat sans"><div class="label">Treasury</div><div class="value bz">{{ shown.treasury.toLocaleString() }} GEN</div></div>
      <div class="stat sans"><div class="label">Released to builders</div><div class="value">{{ shown.released.toLocaleString() }} GEN</div></div>
      <div class="stat sans"><div class="label">Proposals heard</div><div class="value">{{ shown.proposals }}</div></div>
    </div>

    <div class="reveal">
      <div class="eyebrow">The lifecycle</div>
      <div class="sectionlead">Four gates stand between a proposal and the treasury.</div>
    </div>
    <div class="steps">
      <div class="step reveal"><div class="dot">I</div><div class="t">Propose</div><div class="d sans">Name your budget and 2–4 milestones. Every deliverable stated in plain English, on the record.</div></div>
      <div class="step reveal"><div class="dot">II</div><div class="t">Screening</div><div class="d sans">The contract reads your project link and files a public diligence report no one can edit.</div></div>
      <div class="step reveal"><div class="dot">III</div><div class="t">The vote</div><div class="d sans">One wallet, one voice. Quorum seals the verdict into the chain.</div></div>
      <div class="step reveal"><div class="dot">IV</div><div class="t">Release</div><div class="d sans">Each tranche unlocks only after validator consensus inspects the finished milestone.</div></div>
    </div>

    <div class="manifesto reveal">
      <p>"No committee to lobby. No treasurer to trust.<br>The validators read the work, and <b>the code moves the money</b>."</p>
    </div>

    <div class="reveal">
      <div class="eyebrow">On the assembly floor</div>
      <div class="sectionlead">Every proposal, every vote, every verdict — public and permanent.</div>
    </div>
    <div class="props" v-if="featured.length">
      <div class="card prop reveal" v-for="p in featured" :key="p.id" @click="navigate('detail', p.id)">
        <div class="top"><span class="name">{{ p.title }}</span><span class="badge" :class="statusBadge(p).cls">{{ statusBadge(p).text }}</span></div>
        <div class="by sans">by {{ (p.proposer || '').slice(0, 6) }}...{{ (p.proposer || '').slice(-4) }} · {{ p.budget }} GEN</div>
      </div>
    </div>
    <div class="card reveal quiet" v-else>
      <div class="sans quiettext">The floor is quiet. No proposals yet — be the first to address the assembly.</div>
      <button class="btn primary" @click="navigate('profile')">Make a proposal</button>
    </div>
  </main>
</template>

<style scoped>
.hero{position:relative;min-height:100vh;display:flex;align-items:center;background-size:cover;background-position:center 26%;background-attachment:fixed}
.hero .overlay{position:absolute;inset:0;background:var(--overlay)}
.hero .inner{position:relative;width:100%;padding-top:130px;padding-bottom:150px}
.wordmark{font-size:88px;line-height:1.02;letter-spacing:4px;color:#F2E9D4}
.wordmark b{display:block;color:#E8A04C;font-weight:normal}
.netline{font-size:11px;letter-spacing:3px;color:#C4B89F;margin:20px 0 44px;text-transform:uppercase}
.netline i{font-style:normal;color:#E8A04C}
.rotline{font-size:30px;font-weight:normal;color:#F2E9D4;margin-bottom:18px}
.word{display:inline-block;color:#E8A04C;transition:opacity .35s,transform .35s;font-style:italic}
.word.out{opacity:0;transform:translateY(12px)}
.sub{font-size:15.5px;color:#C4B89F;max-width:470px;margin:0 0 36px;line-height:1.75}
.heroghost{margin-left:10px;background:rgba(4,12,16,0.5);color:#E9DFC9;border:1px solid rgba(233,223,201,0.35)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:-72px;position:relative;z-index:5;margin-bottom:110px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:24px 22px}
.stat .label{font-size:10px;letter-spacing:2px;color:var(--ink2);text-transform:uppercase}
.stat .value{font-size:28px;margin-top:10px;color:var(--ink)}
.stat .value.bz{color:var(--bronze-hi)}
.sectionlead{font-size:28px;max-width:520px;line-height:1.35;margin-bottom:46px}
.steps{display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin-bottom:110px;position:relative}
.steps::before{content:"";position:absolute;top:26px;left:6%;right:6%;height:1px;background:var(--line)}
.step{padding:0 18px;position:relative}
.step .dot{width:52px;height:52px;border-radius:50%;background:var(--card);border:1px solid var(--bronze);color:var(--bronze-hi);display:flex;align-items:center;justify-content:center;font-size:18px;font-style:italic;margin-bottom:18px;position:relative;z-index:2}
.step .t{font-size:17px;margin-bottom:8px}
.step .d{font-size:12.5px;color:var(--ink2);line-height:1.7}
.manifesto{text-align:center;padding:30px 20px 110px}
.manifesto p{font-size:26px;font-style:italic;line-height:1.5;max-width:640px;margin:0 auto;color:var(--ink)}
.manifesto p b{color:var(--bronze-hi);font-weight:normal}
.props{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:60px}
.prop{cursor:pointer}
.prop:hover{border-color:var(--bronze)}
.prop .top{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;gap:10px}
.prop .name{font-size:17px}
.prop .by{font-size:11px;color:var(--ink2);letter-spacing:.5px}
.quiet{text-align:center;padding:48px 24px;margin-bottom:60px}
.quiettext{font-size:14px;color:var(--ink2);margin-bottom:22px;line-height:1.7}
@media(max-width:760px){
.wordmark{font-size:46px}.rotline{font-size:24px}
.stats{grid-template-columns:1fr 1fr;margin-top:-50px}
.steps{grid-template-columns:1fr;gap:26px}.steps::before{display:none}
.props{grid-template-columns:1fr}.sectionlead{font-size:22px}.manifesto p{font-size:20px}}
</style>
