import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import path from 'path'

// frontendRoute drives the plugin's Frappe defaults: it builds to
// apna_slot/public/frontend, sets base to /assets/apna_slot/frontend/, and
// writes the rendered index.html to apna_slot/www/apnaslot.html.
export default defineConfig({
  plugins: [frappeui({ frontendRoute: '/apnaslot' }), vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  optimizeDeps: {
    exclude: ['frappe-ui'],
    include: ['tippy.js', 'engine.io-client', 'socket.io-client', 'debug'],
  },
})
