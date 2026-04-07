import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Progress from './views/Progress.vue'
import Results from './views/Results.vue'
import TodoList from './views/TodoList.vue'
import History from './views/History.vue'
import './style.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/progress' },
    { path: '/progress', component: Progress },
    { path: '/results', component: Results },
    { path: '/todo', component: TodoList },
    { path: '/history', component: History },
  ]
})

createApp(App).use(router).mount('#app')
