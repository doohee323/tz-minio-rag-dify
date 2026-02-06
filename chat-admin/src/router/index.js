import Vue from 'vue'
import VueRouter from 'vue-router'
import Intro from '../views/Intro.vue'
import Chat from '../views/Chat.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import Admin from '../views/Admin.vue'
import AdminSystems from '../views/AdminSystems.vue'

Vue.use(VueRouter)

const routes = [
  { path: '/', name: 'Intro', component: Intro },
  { path: '/login', name: 'Login', component: Login },
  { path: '/register', name: 'Register', component: Register },
  { path: '/admin', name: 'Admin', component: Admin },
  { path: '/admin/systems', name: 'AdminSystems', component: AdminSystems },
  { path: '/chat', name: 'Chat', component: Chat }
]

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes
})

export default router
