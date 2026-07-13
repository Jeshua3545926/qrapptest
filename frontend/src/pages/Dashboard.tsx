import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import axios from 'axios'
import Sidebar from '../components/Sidebar'
import { 
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts'
import {
  Users, TrendingUp,
  Building, ArrowUpRight, ArrowDownRight
} from 'lucide-react'
import { API_BASE } from '../utils/api'

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function Dashboard() {
  const [registros, setRegistros] = useState<any[]>([])
  const [empleados, setEmpleados] = useState<any[]>([])
  const [, setLocales] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')
  
  const { logout, user } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    fetchDashboardData()
  }, [timeRange])

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('jwt_token')
      const [registrosRes, empleadosRes, localesRes] = await Promise.all([
        axios.get(`${API_BASE}/admin`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_BASE}/empleados`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_BASE}/admin/locales`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ])
      setRegistros(registrosRes.data.registros || [])
      setEmpleados(empleadosRes.data || [])
      setLocales(localesRes.data || [])
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const filterByTimeRange = (data: any[]) => {
    const now = new Date()
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
    const cutoff = new Date(now.getTime() - days * 24 * 60 * 60 * 1000)
    return data.filter(item => new Date(item.fecha) >= cutoff)
  }

  const filteredRegistros = filterByTimeRange(registros)

  // Calculate metrics
  const totalRegistros = filteredRegistros.length
  const totalEmpleados = empleados.length
  const totalLocales = new Set(filteredRegistros.map(r => r.local)).size
  const avgRegistrosPerDay = totalRegistros / (timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90)

  // Attendance by local
  const attendanceByLocal = filteredRegistros.reduce((acc, reg) => {
    acc[reg.local] = (acc[reg.local] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const localData = Object.entries(attendanceByLocal).map(([local, count]) => ({
    name: local,
    value: count
  }))

  // Attendance by employee
  const attendanceByEmployee = filteredRegistros.reduce((acc, reg) => {
    acc[reg.empleado] = (acc[reg.empleado] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const employeeData = (Object.entries(attendanceByEmployee) as [string, number][])
    .map(([name, count]) => ({ name, count: Number(count) }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10)

  // Attendance over time
  const attendanceOverTime = filteredRegistros.reduce((acc, reg) => {
    const date = new Date(reg.fecha).toLocaleDateString()
    acc[date] = (acc[date] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const timeData = Object.entries(attendanceOverTime)
    .map(([date, count]) => ({ date, count }))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
        <div className="text-gray-900 text-xl">Cargando...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50">
      <Sidebar user={user || undefined} onLogout={handleLogout} />
      
      <div className="ml-64 p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>

        {/* Time Range Selector */}
        <div className="flex gap-2 mb-6">
          {(['7d', '30d', '90d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-2 rounded-lg transition-all ${
                timeRange === range
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              {range === '7d' ? '7 días' : range === '30d' ? '30 días' : '90 días'}
            </button>
          ))}
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard
            icon={<Users className="w-6 h-6" />}
            title="Total Registros"
            value={totalRegistros}
            change={12}
            color="blue"
          />
          <StatCard
            icon={<Users className="w-6 h-6" />}
            title="Empleados Activos"
            value={totalEmpleados}
            change={5}
            color="green"
          />
          <StatCard
            icon={<Building className="w-6 h-6" />}
            title="Locales"
            value={totalLocales}
            change={0}
            color="purple"
          />
          <StatCard
            icon={<TrendingUp className="w-6 h-6" />}
            title="Promedio Diario"
            value={avgRegistrosPerDay.toFixed(1)}
            change={8}
            color="orange"
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Attendance Over Time */}
          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Asistencia en el Tiempo</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={timeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" stroke="#6b7280" />
                <YAxis stroke="#6b7280" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                  itemStyle={{ color: '#1f2937' }}
                />
                <Legend />
                <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Attendance by Local */}
          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Asistencia por Local</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={localData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="name" stroke="#6b7280" />
                <YAxis stroke="#6b7280" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                  itemStyle={{ color: '#1f2937' }}
                />
                <Legend />
                <Bar dataKey="value" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top Employees */}
          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Top 10 Empleados</h3>
            <div className="space-y-3">
              {employeeData.map((emp, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-bold">
                      {index + 1}
                    </div>
                    <span className="text-gray-900">{emp.name}</span>
                  </div>
                  <span className="text-gray-600 font-semibold">{emp.count} registros</span>
                </div>
              ))}
            </div>
          </div>

          {/* Attendance Distribution */}
          <div className="bg-white rounded-xl p-8 border border-gray-200 shadow-sm">
            <h3 className="text-lg font-bold text-gray-900 mb-6">Distribución por Local</h3>
            <ResponsiveContainer width="100%" height={350}>
              <PieChart>
                <Pie
                  data={localData}
                  cx="50%"
                  cy="50%"
                  labelLine={true}
                  label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                  outerRadius={100}
                  innerRadius={40}
                  paddingAngle={5}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {localData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '12px' }}
                  itemStyle={{ color: '#1f2937' }}
                />
                <Legend 
                  verticalAlign="bottom" 
                  height={36}
                  iconType="circle"
                  wrapperStyle={{ paddingTop: '20px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ 
  icon, 
  title, 
  value, 
  change, 
  color 
}: { 
  icon: React.ReactNode
  title: string
  value: string | number
  change: number
  color: 'blue' | 'green' | 'purple' | 'orange'
}) {
  const colorClasses = {
    blue: 'from-blue-50 to-blue-100 border-blue-200',
    green: 'from-green-50 to-green-100 border-green-200',
    purple: 'from-purple-50 to-purple-100 border-purple-200',
    orange: 'from-orange-50 to-orange-100 border-orange-200'
  }

  const iconColors = {
    blue: 'text-blue-600',
    green: 'text-green-600',
    purple: 'text-purple-600',
    orange: 'text-orange-600'
  }

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} rounded-xl p-6 border shadow-sm`}>
      <div className="flex items-center justify-between mb-4">
        <div className={iconColors[color]}>{icon}</div>
        <div className={`flex items-center gap-1 text-sm ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {change >= 0 ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
          {change}%
        </div>
      </div>
      <div className="text-3xl font-bold text-gray-900">{value}</div>
      <div className="text-gray-600 mt-1">{title}</div>
    </div>
  )
}
