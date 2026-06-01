import { VueQueryPlugin } from '@tanstack/vue-query'
import { createApp } from 'vue'

import App from './App.vue'
import './style.css'
import router from './router'
import { useAuth } from './stores/auth'

const app = createApp(App)

app.use(router)
app.use(VueQueryPlugin)

// Restore the session (if a token exists) before mounting so the navbar
// renders in the correct logged-in/out state on first paint.
const { init } = useAuth()
init().finally(() => {
  app.mount('#app')
})
