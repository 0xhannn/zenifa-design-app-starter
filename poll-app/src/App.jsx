import { Navigate, Route, Routes } from 'react-router-dom'
import CreatePoll from './components/CreatePoll'
import VotePoll from './components/VotePoll'
import PollHistory from './components/PollHistory'
import PollStats from './components/PollStats'

/**
 * Embed-only routes. Chrome (favicon, topnav, mobile tabs) comes from main
 * Workflow Planner shell (static/index.html) when menu=poll — no second header.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/poll" replace />} />
      <Route path="/poll" element={<PollHistory />} />
      <Route path="/poll/new" element={<CreatePoll />} />
      {/* stats BEFORE :pollId so path doesn't get swallowed */}
      <Route path="/poll/:pollId/stats" element={<PollStats />} />
      <Route path="/poll/:pollId" element={<VotePoll />} />
      <Route path="*" element={<Navigate to="/poll" replace />} />
    </Routes>
  )
}
