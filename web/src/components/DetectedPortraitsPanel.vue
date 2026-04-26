<template>
  <div class="card">
    <div class="card-body">
      <div class="portraits-header" @click="expanded = !expanded">
        <h5 class="mb-0">Friendship Levels<span class="portrait-count-badge" v-if="portraits.length">{{ portraits.length }}</span></h5>
        <span class="toggle-text">{{ expanded ? '▲' : '▼' }}</span>
      </div>
      <div v-if="expanded" class="portraits-body">
        <div v-if="portraits.length === 0" class="empty-state">No characters detected yet</div>
        <div v-else class="portraits-grid">
          <div v-for="p in portraits" :key="p.name" class="portrait-item" :class="{ 'portrait-npc': p.is_npc }">
            <div class="portrait-img-wrap">
              <img :src="'/training-icon/' + p.name" :alt="p.name" class="portrait-img" @error="onImgError">
            </div>
            <div class="portrait-name">{{ formatName(p.name) }}</div>
            <div class="badge-container">
              <div class="portrait-type-badge" :class="p.is_npc ? 'badge-npc' : 'badge-deck'">{{ p.is_npc ? 'NPC' : 'Deck' }}</div>
              <div v-if="p.card_type && p.card_type !== 'Unknown' && p.card_type !== 'NPC'" class="portrait-type-badge" :class="getCardTypeClass(p.card_type)">{{ p.card_type }}</div>
            </div>
            <div class="favor-bar">
              <div class="favor-pip" v-for="i in 4" :key="i" :class="{ filled: i <= p.favor, ['lv' + p.favor]: i <= p.favor }"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "DetectedPortraitsPanel",
  props: {
    portraits: { type: Array, default: () => [] }
  },
  data() {
    return { expanded: true }
  },
  methods: {
    formatName(n) {
      return n.replace(/_/g, ' ')
    },
    onImgError(e) {
      e.target.style.display = 'none'
    },
    getCardTypeClass(type) {
      if (!type) return '';
      const t = type.toLowerCase();
      return `badge-type-${t}`;
    }
  }
}
</script>

<style scoped>
.portraits-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  padding: 2px 0;
}
.portraits-header:hover { opacity: .85 }
.toggle-text { color: var(--muted); font-size: 12px }
.portrait-count-badge {
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
.portraits-body { margin-top: 12px }
.portraits-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.portrait-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 4px;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 10px;
  background: rgba(255,255,255,.02);
  transition: all .2s;
}
.portrait-item:hover {
  border-color: var(--accent);
  background: rgba(255,255,255,.04);
}
.portrait-npc {
  border-color: rgba(255,255,255,.05);
  opacity: .75;
}
.portrait-img-wrap {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid rgba(255,255,255,.15);
  margin-bottom: 6px;
}
.portrait-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.portrait-name {
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80px;
  margin-bottom: 4px;
}
.badge-container {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: center;
  margin-bottom: 4px;
}
.portrait-type-badge {
  font-size: 8px;
  font-weight: 800;
  padding: 1px 4px;
  border-radius: 3px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  line-height: 1;
}
.badge-deck {
  background: rgba(42, 192, 255, .2);
  color: #2ac0ff;
}
.badge-npc {
  background: rgba(255,255,255,.08);
  color: rgba(255,255,255,.45);
}

.badge-type-speed { background: rgba(42, 192, 255, .2); color: #2ac0ff; }
.badge-type-stamina { background: rgba(255, 100, 100, .2); color: #ff6464; }
.badge-type-power { background: rgba(255, 173, 30, .2); color: #ffad1e; }
.badge-type-guts { background: rgba(255, 100, 200, .2); color: #ff64c8; }
.badge-type-wits { background: rgba(162, 230, 30, .2); color: #a2e61e; }
.badge-type-friend { background: rgba(180, 100, 255, .2); color: #b464ff; }
.badge-type-group { background: rgba(100, 150, 255, .2); color: #6496ff; }

.favor-bar {
  display: flex;
  gap: 3px;
}
.favor-pip {
  width: 10px;
  height: 4px;
  border-radius: 2px;
  background: rgba(255,255,255,.12);
  transition: all .2s;
}
.favor-pip.filled.lv1 { background: #2ac0ff }
.favor-pip.filled.lv2 { background: #a2e61e }
.favor-pip.filled.lv3 { background: #ffad1e }
.favor-pip.filled.lv4 { background: #ffeb78 }
.empty-state { color: var(--muted); font-size: 13px; padding: 8px 0 }
</style>
