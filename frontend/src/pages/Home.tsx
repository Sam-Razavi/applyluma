import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div className="max-w-2xl mx-auto text-center py-20">
      <h1 className="text-5xl font-bold text-gray-900 mb-6 leading-tight">
        Track every application,{' '}
        <span className="text-indigo-600">land your dream job.</span>
      </h1>
      <p className="text-xl text-gray-500 mb-10">
        ApplyLuma keeps your job search organized with smart tracking,
        status updates, and actionable insights.
      </p>
      <Link
        to="/register"
        className="inline-block bg-indigo-600 text-white text-lg px-8 py-3 rounded-xl hover:bg-indigo-700 transition-colors"
      >
        Start for free
      </Link>
    </div>
  )
}
