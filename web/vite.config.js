import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Visit requests are relayed to the OneAquaHealth FHIR sandbox, limited to that one record type.
const relay = {
  '/fhir-relay/ServiceRequest': {
    target: 'https://sandbox.hl7europe.eu',
    changeOrigin: true,
    rewrite: (path) => path.replace('/fhir-relay', '/oneaquahealth/fhir'),
    configure: (proxy) => proxy.on('proxyReq', (req) => req.removeHeader('origin')),
  },
}

export default defineConfig({
  plugins: [react()],
  base: './',
  server: { proxy: relay },
  preview: { proxy: relay },
})
