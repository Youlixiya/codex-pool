import { createRouter, createWebHistory } from "vue-router";
import Login from "./views/Login.vue";
import Layout from "./views/Layout.vue";
import Dashboard from "./views/Dashboard.vue";
import ApiKeys from "./views/ApiKeys.vue";
import Upstreams from "./views/Upstreams.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: Login },
    {
      path: "/",
      component: Layout,
      children: [
        { path: "", component: Dashboard },
        { path: "api-keys", component: ApiKeys },
        { path: "upstreams", component: Upstreams },
      ],
    },
  ],
});

router.beforeEach((to) => {
  if (to.path !== "/login" && !localStorage.getItem("token")) {
    return "/login";
  }
});

export default router;
