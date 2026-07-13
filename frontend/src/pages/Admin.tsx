import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import axios from 'axios'
import Sidebar from '../components/Sidebar'
import { API_BASE } from '../utils/api'

export default function Admin() {
  const [registros, setRegistros] = useState<any[]>([])
  const [, setQrTokens] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showGenerateQR, setShowGenerateQR] = useState(false)
  
  const { logout, user } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('jwt_token')
      const [registrosRes] = await Promise.all([
        axios.get(`${API_BASE}/admin`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_BASE}/admin/locales`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ])
      setRegistros(registrosRes.data.registros)
      setQrTokens(registrosRes.data.qr_tokens)
    } catch (error) {
      console.error('Error fetching data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const handleDownloadExcel = async () => {
    try {
      const token = localStorage.getItem('jwt_token')
      const response = await axios.get(`${API_BASE}/admin/descargar-registros`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `registros_${Date.now()}.xlsx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Error downloading excel:', error)
    }
  }

  const handleDeleteRegistro = async (id: string) => {
    if (!confirm('¿Estás seguro de eliminar este registro?')) return

    try {
      const token = localStorage.getItem('jwt_token')
      await axios.delete(`${API_BASE}/api/registros/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setRegistros(registros.filter(reg => reg.id !== id))
    } catch (error) {
      console.error('Error deleting registro:', error)
      alert('Error al eliminar registro')
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Cargando...</div>
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <Sidebar user={user || undefined} onLogout={handleLogout} />
      
      <div className="ml-64 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Panel Admin</h1>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <button
            onClick={() => setShowGenerateQR(!showGenerateQR)}
            className="bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors"
          >
            {showGenerateQR ? 'Ocultar Generador QR' : 'Generar QR'}
          </button>
          <button
            onClick={handleDownloadExcel}
            className="bg-green-600 text-white py-3 px-6 rounded-lg hover:bg-green-700 transition-colors"
          >
            Descargar Registros Excel
          </button>
          <button
            onClick={() => navigate('/qr-list')}
            className="bg-purple-600 text-white py-3 px-6 rounded-lg hover:bg-purple-700 transition-colors"
          >
            Ver Todos los QRs
          </button>
          <button
            onClick={() => navigate('/empleados')}
            className="bg-orange-600 text-white py-3 px-6 rounded-lg hover:bg-orange-700 transition-colors"
          >
            Gestionar Empleados
          </button>
        </div>

        {showGenerateQR && (
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm mb-8">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Generar QR Personalizado</h2>
            <GenerateQRForm onSuccess={fetchData} onCancel={() => setShowGenerateQR(false)} />
          </div>
        )}

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-bold text-gray-900">Registros Recientes</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Empleado</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Local</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Fecha</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Observaciones</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {registros.map((reg) => (
                  <tr key={reg.id} className="border-b border-gray-200 hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-900">{reg.empleado}</td>
                    <td className="px-4 py-3 text-gray-600">{reg.local}</td>
                    <td className="px-4 py-3 text-gray-600">{new Date(reg.fecha).toLocaleString()}</td>
                    <td className="px-4 py-3 text-gray-600">{reg.observaciones || '-'}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDeleteRegistro(reg.id)}
                        className="text-red-600 hover:text-red-700 font-medium text-sm"
                      >
                        Eliminar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

function GenerateQRForm({ onSuccess, onCancel }: { onSuccess: () => void, onCancel: () => void }) {
  const [nombreLocal, setNombreLocal] = useState('')
  const [nombreEmpleado, setNombreEmpleado] = useState('')
  const [fecha, setFecha] = useState('')
  const [hora, setHora] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const API_BASE = import.meta.env.VITE_API_BASE?.trim() || `${window.location.protocol}//${window.location.hostname}:5000`

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const token = localStorage.getItem('jwt_token')
      await axios.post(
        `${API_BASE}/admin/generar-qr`,
        { nombre_local: nombreLocal, nombre_empleado: nombreEmpleado, fecha, hora },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      onSuccess()
      setNombreLocal('')
      setNombreEmpleado('')
      setFecha('')
      setHora('')
    } catch (error: any) {
      setError(error.response?.data?.error || 'Error al generar QR')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-gray-700 mb-2">Nombre Local</label>
          <input
            type="text"
            value={nombreLocal}
            onChange={(e) => setNombreLocal(e.target.value)}
            className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
        <div>
          <label className="block text-gray-700 mb-2">Nombre Empleado</label>
          <input
            type="text"
            value={nombreEmpleado}
            onChange={(e) => setNombreEmpleado(e.target.value)}
            className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
        <div>
          <label className="block text-gray-700 mb-2">Fecha</label>
          <input
            type="date"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
            className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
        <div>
          <label className="block text-gray-700 mb-2">Hora</label>
          <input
            type="time"
            value={hora}
            onChange={(e) => setHora(e.target.value)}
            className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg mb-4">
          {error}
        </div>
      )}

      <div className="flex gap-4">
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Generando...' : 'Generar QR'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-colors"
        >
          Cancelar
        </button>
      </div>
    </form>
  )
}
