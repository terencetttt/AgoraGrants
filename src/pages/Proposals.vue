<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { navigate } from '../store'
import { getAllProposals } from '../client'

const loading = ref(true)
const failed = ref(false)
const proposals = ref<any[]>([])
const filter = ref('ALL')
const filters = ['ALL', 'SUBMITTED', 'SCREENED', 'APPROVED', 'REJECTED', 'COMPLETE']

const visible = computed(() => {
  if (filter.value === 'ALL') return [...proposals.value].reverse()
  return proposals.value.filter(p => (p.status || '').toUpperCase() === filter.value).reverse()
})

function badge(p: any): { text: string, cls: string } {
  const s = (p.status || '').toUpperCase()
  if (s === 'APPROVED') return { text: 'FUNDED', cls: 'bronze' }
  if (s === 'COMPLETE') return { text: 'COMPLETE', cls: 'green' }
  if (s === 'REJECTED') return { text: 'REJECTED', cls: 'red' }
  if (s === 'SCREENED') return { text: 'VOTING · ' + (p.votes_yes || 0) + 'Y / ' + (p.votes_no || 0) + 'N', cls: 'green' }
  return { text: 'AWAITING SCREENING', cls: 'gray' }
}

onMounted(async () => {
  try {
    const all = await getAllProposals()
    proposals.value = Array.isArray(all) ? all : []
  } catch { failed.value = true }
  loading.value = false
})
</script>

<template>
  <div class="container pagepad">
    <div class="eyebrow">The assembly floor</div>
    <h1 class="pagetitle">Proposals</h1>

    <div class="filterrow sans">
      <button v-for="f in filters" :key="f" class="filterbtn"
        :class="{ active: filter === f }" @click="filter = f">{{ f }}</button>
    </div>

    <div v-if="loading" class="card note sans">Reading the chain...</div>
    <div v-else-if="failed" class="card note sans">Could not reach the contract. Is the address configured and the network up?</div>
    <div v-else-if="!visible.length" class="card note sans">
      Nothing here under "{{ filter }}".
      <span v-if="filter === 'ALL'">The floor is quiet — <a class="link" @click="navigate('profile')">make the first proposal</a>.</span>
    </div>

    <div class="list" v-else>
      <div class="card row" v-for="p in visible" :key="p.id" @click="navigate('detail', p.id)">
        <div class="rowmain">
          <div class="rowtop">
            <span class="name">#{{ p.id }} · {{ p.title }}</span>
            <span class="badge" :class="badge(p).cls">{{ badge(p).text }}</span>
          </div>
          <div class="meta sans">by {{ (p.proposer || '').slice(0, 6) }}...{{ (p.proposer || '').slice(-4) }} · {{ p.budget }} GEN requested</div>
        </div>
        <div class="arrow">→</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pagetitle{font-weight:normal;font-size:40px;margin-bottom:30px}
.filterrow{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:26px}
.filterbtn{background:transparent;border:1px solid var(--line);color:var(--ink2);font-size:10px;letter-spacing:1.5px;padding:7px 14px;border-radius:20px;transition:all .2s}
.filterbtn:hover{border-color:var(--bronze);color:var(--ink)}
.filterbtn.active{background:var(--bronze);border-color:var(--bronze);color:#08141A;font-weight:bold}
.note{color:var(--ink2);font-size:13.5px;line-height:1.7}
.link{color:var(--bronze-hi);cursor:pointer;text-decoration:underline}
.list{display:flex;flex-direction:column;gap:12px}
.row{display:flex;align-items:center;justify-content:space-between;cursor:pointer;transition:border-color .2s}
.row:hover{border-color:var(--bronze)}
.rowmain{flex:1;min-width:0}
.rowtop{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:6px}
.name{font-size:17px}
.meta{font-size:11.5px;color:var(--ink2);letter-spacing:.5px}
.arrow{color:var(--bronze-hi);font-size:18px;margin-left:16px}
@media(max-width:700px){.rowtop{flex-direction:column;align-items:flex-start;gap:6px}}
</style>
