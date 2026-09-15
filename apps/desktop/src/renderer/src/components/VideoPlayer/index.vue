<template>
  <div class="video-player-host-wrap">
    <video v-if="src" class="video-player-host" :src="src" controls autoplay playsinline />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  src: string
}>()
</script>

<style scoped lang="less">
.video-player-host-wrap {
  position: absolute;
  inset: 0;
  background: #111;
}

.video-player-host {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #111;
}
</style>
