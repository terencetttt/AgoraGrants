<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { store, navigate, setTheme } from './store'
import { connectWallet, switchWallet, onAccountsChanged } from './client'
import Home from './pages/Home.vue'
import Proposals from './pages/Proposals.vue'
import Detail from './pages/Detail.vue'
import Profile from './pages/Profile.vue'

const pages: Record<string, any> = { home: Home, proposals: Proposals, detail: Detail, profile: Profile }
const current = computed(() => pages[store.page])
const shortWallet = computed(() =>
  store.wallet ? store.wallet.slice(0, 6) + '...' + store.wallet.slice(-4) : null
)
const switching = ref(false)

async function onConnect() {
  try { store.wallet = await connectWallet() }
  catch (e: any) { alert(e.message || 'Could not connect wallet') }
}
async function onSwitchWallet() {
  switching.value = true
  try { store.wallet = await switchWallet() }
  catch (e: any) { alert(e.message || 'Could not switch wallet') }
  switching.value = false
}
onMounted(() => {
  setTheme(store.theme)
  onAccountsChanged((address) => { store.wallet = address })
})
</script>

<template>
  <nav class="topnav">
    <div class="brand sans" @click="navigate('home')"><span>A</span>.</div>
    <div class="navlinks sans">
      <a @click="navigate('proposals')">Proposals</a>
      <a @click="navigate('profile')">Submit</a>
      <a @click="navigate('profile')">Profile</a>
      <button class="modebtn" @click="setTheme(store.theme === 'dark' ? 'light' : 'dark')">{{ store.theme === 'dark' ? 'LIGHT' : 'DARK' }}</button>
      <template v-if="shortWallet">
        <span class="wallet">{{ shortWallet }}</span>
        <button class="switchbtn sans" :disabled="switching" @click="onSwitchWallet" title="If nothing happens, open Rabby and pick a different account there — this updates automatically">{{ switching ? '...' : 'SWITCH' }}</button>
      </template>
      <button v-else class="wallet connectbtn" @click="onConnect">CONNECT</button>
    </div>
  </nav>

  <component :is="current" />

  <footer class="sans">
    A MILESTONE-VERIFIED GRANT DAO<br>
    <span class="addr">GHAZA · GENLAYER BUILDER PROGRAM</span>
  </footer>
</template>

<style scoped>
.topnav{position:fixed;top:0;left:0;right:0;z-index:50;display:flex;align-items:center;justify-content:space-between;padding:14px 34px;background:rgba(4,12,16,0.6);backdrop-filter:blur(10px);border-bottom:1px solid rgba(233,223,201,0.12)}
[data-theme="light"] .topnav{background:rgba(245,241,232,0.78);border-bottom:1px solid var(--line)}
.brand{font-size:20px;color:var(--ink);font-weight:bold;border-bottom:2px solid var(--bronze);padding-bottom:2px;cursor:pointer}
.brand span{color:var(--bronze-hi)}
.navlinks{display:flex;align-items:center;gap:16px}
.navlinks a{color:var(--ink2);font-size:12px;letter-spacing:1px;cursor:pointer}
.navlinks a:hover{color:var(--bronze-hi)}
.modebtn{background:none;border:none;font-size:10.5px;letter-spacing:2px;color:var(--ink2);padding:4px 0 3px;border-bottom:2px solid var(--line);transition:color .25s,border-color .25s;font-family:Verdana,'Segoe UI',Arial,sans-serif;cursor:pointer}
.modebtn:hover{color:var(--bronze-hi);border-bottom-color:var(--bronze)}
.wallet{font-size:11px;padding:5px 13px;border-radius:20px;background:var(--bronze-soft);color:var(--bronze-hi);border:1px solid var(--bronze);letter-spacing:.5px}
.connectbtn{background:var(--bronze);color:#08141A;font-weight:bold;cursor:pointer}
.switchbtn{background:transparent;border:1px solid var(--line);color:var(--ink2);font-size:9.5px;letter-spacing:1.5px;padding:5px 11px;border-radius:20px;cursor:pointer}
.switchbtn:hover{color:var(--bronze-hi);border-color:var(--bronze)}
footer{text-align:center;padding:36px 20px;border-top:1px solid var(--line);font-size:11px;color:var(--ink2);letter-spacing:1.5px;line-height:2.2}
footer .addr{color:var(--bronze)}
@media(max-width:700px){.navlinks a{display:none}}
</style>
