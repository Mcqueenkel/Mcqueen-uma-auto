<template>
  <div class="card">
    <div class="card-body">
      <div class="detected-items-header" @click="expanded = !expanded">
        <h5 class="mb-0">Owned Items <span class="item-count-badge" v-if="items.length">{{ items.length }}</span></h5>
        <span class="toggle-text">{{ expanded ? '▲' : '▼' }}</span>
      </div>
      <div v-if="expanded" class="detected-items-body">
        <div v-if="items.length === 0" class="empty-state">No items detected yet</div>
        <div v-else class="detected-items-list">
          <div v-for="item in sortedItems" :key="item.name" class="detected-item-row">
            <div class="item-info">
              <img v-if="getItemIcon(item.name)" :src="getItemIcon(item.name)" :alt="item.name" class="item-icon" />
              <span class="item-name">{{ item.name }}</span>
            </div>
            <span class="item-qty">×{{ item.qty }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
const iconModules = import.meta.glob('../assets/img/mant_items/*.png', { eager: true })

const iconMap = {}
for (const path in iconModules) {
  const filename = path.split('/').pop().replace('.png', '')
  iconMap[filename] = iconModules[path].default
}

function nameToSlug(displayName) {
  return displayName.toLowerCase().replace(/'/g, '').replace(/ /g, '_')
}

export default {
  name: "DetectedItemsPanel",
  props: {
    items: { type: Array, default: () => [] }
  },
  data() {
    return { expanded: true }
  },
  computed: {
    sortedItems() {
      return [...this.items].sort((a, b) => a.name.localeCompare(b.name))
    }
  },
  methods: {
    getItemIcon(name) {
      return iconMap[nameToSlug(name)] || null
    }
  }
}
</script>

<style scoped>
.detected-items-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  padding: 2px 0;
}
.detected-items-header:hover { opacity: .85 }
.toggle-text { color: var(--muted); font-size: 12px }
.item-count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 9999px;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  margin-left: 8px;
  vertical-align: middle;
}
.detected-items-body { margin-top: 12px }
.detected-items-list { display: flex; flex-direction: column; gap: 6px; max-height: 320px; overflow-y: auto }
.detected-item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 8px;
  background: rgba(255,255,255,.02);
  transition: all .2s;
}
.detected-item-row:hover {
  border-color: var(--accent);
  background: rgba(255,255,255,.04);
}
.item-info { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1 }
.item-icon { width: 28px; height: 28px; border-radius: 4px; object-fit: contain; flex-shrink: 0 }
.item-name { font-weight: 600; font-size: 13px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.item-qty { font-size: 13px; font-weight: 700; color: var(--accent); white-space: nowrap; flex-shrink: 0; margin-left: 8px }
.empty-state { color: var(--muted); font-size: 13px; padding: 8px 0 }
</style>

