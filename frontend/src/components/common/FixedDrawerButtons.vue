<template>
  <div class="fixed-drawer-buttons" :class="{ 'with-padding': withPadding }">
    <slot></slot>
  </div>
</template>

<script setup>
defineProps({
  withPadding: {
    type: Boolean,
    default: true
  }
});
</script>

<style lang="scss" scoped>
.fixed-drawer-buttons {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 10;
  background-color: #fff;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: flex-end;
  align-items: center;
  height: 64px;
  
  &.with-padding {
    padding: 0 20px;
  }
}
</style> 