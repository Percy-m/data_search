<template>
  <el-config-provider>
    <div class="app-wrapper">
      <el-header height="60px" class="header">
        <h1>数据可视化报表平台</h1>
      </el-header>
      <el-main class="main-content">
        <BiDashboard />
      </el-main>
    </div>
  </el-config-provider>
</template>

<script setup>
import BiDashboard from './components/BiDashboard.vue'
</script>

<style scoped>
.app-wrapper {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  background-color: #242f42;
  color: #fff;
  display: flex;
  align-items: center;
}
.header h1 {
  margin: 0;
  font-size: 20px;
}
.main-content {
  flex: 1;
  background-color: #f0f2f5;
  padding: 20px;
}
</style>