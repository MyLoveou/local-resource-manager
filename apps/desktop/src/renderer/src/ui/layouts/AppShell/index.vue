<template>
  <div class="app-shell">
    <slot name="top" />
    <slot name="banner" />
    <div class="app-shell__body">
      <slot name="sidebar" />
      <main class="app-shell__main">
        <slot />
        <slot name="selection" />
      </main>
      <slot name="inspector" />
    </div>
  </div>
</template>

<style scoped lang="less">
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.app-shell__body {
  display: flex;
  flex: 1;
  min-height: 0;
}

.app-shell__main {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
</style>
