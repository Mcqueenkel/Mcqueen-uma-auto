<template>
  <div class="card">
    <div class="card-body">
      <div class="detected-skills-header" @click="expanded = !expanded">
        <h5 class="mb-0">Detected Skills <span class="skill-count-badge" v-if="skills.length">{{ skills.length }}</span></h5>
        <span class="toggle-text">{{ expanded ? '▲' : '▼' }}</span>
      </div>
      <div v-if="expanded" class="detected-skills-body">
        <div v-if="skills.length === 0" class="empty-state">No skills detected yet</div>
        <div v-else class="detected-skills-list">
          <div v-for="skill in sortedSkills" :key="skill.name" class="detected-skill-row" :class="{ gold: skill.gold }">
            <div class="skill-info">
              <span class="skill-name">{{ skill.name }}</span>
              <span v-if="skill.cost > 0" class="skill-cost">{{ skill.cost }}pt</span>
            </div>
            <div class="skill-meta">
              <span v-if="skill.hint_level > 0" class="hint-tag">Lv{{ skill.hint_level }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "DetectedSkillsPanel",
  props: {
    skills: { type: Array, default: () => [] }
  },
  data() {
    return { expanded: true }
  },
  computed: {
    sortedSkills() {
      return [...this.skills].sort((a, b) => {
        if (a.gold !== b.gold) return a.gold ? -1 : 1
        if (a.hint_level !== b.hint_level) return b.hint_level - a.hint_level
        return a.name.localeCompare(b.name)
      })
    }
  }
}
</script>

<style scoped>
.detected-skills-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  padding: 2px 0;
}
.detected-skills-header:hover { opacity: .85 }
.toggle-text { color: var(--muted); font-size: 12px }
.skill-count-badge {
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
.detected-skills-body { margin-top: 12px }
.detected-skills-list { display: flex; flex-direction: column; gap: 6px; max-height: 280px; overflow-y: auto }
.detected-skill-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 8px;
  background: rgba(255,255,255,.02);
  transition: all .2s;
}
.detected-skill-row:hover {
  border-color: var(--accent);
  background: rgba(255,255,255,.04);
}
.detected-skill-row.gold {
  border-color: rgba(255,200,50,.3);
  background: rgba(255,200,50,.04);
}
.detected-skill-row.gold:hover {
  border-color: rgba(255,200,50,.5);
}
.skill-info { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1 }
.skill-name { font-weight: 600; font-size: 13px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.detected-skill-row.gold .skill-name { color: #ffd966 }
.skill-cost { font-size: 11px; color: var(--muted); white-space: nowrap }
.skill-meta { display: flex; align-items: center; gap: 6px; flex-shrink: 0 }
.hint-tag {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 9999px;
  border: 1px solid var(--accent);
  color: var(--accent);
  font-weight: 700;
}
.empty-state { color: var(--muted); font-size: 13px; padding: 8px 0 }
</style>

