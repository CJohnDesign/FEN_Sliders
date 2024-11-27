import { defineAppSetup } from '@slidev/types'
import SlideAudio from '../components/SlideAudio.vue'

export default defineAppSetup(({ app }) => {
  app.component('SlideAudio', SlideAudio)
})