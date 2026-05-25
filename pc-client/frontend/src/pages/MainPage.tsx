export default function MainPage() {
  return (
    <div className="flex flex-col h-screen">
      {/* StatusBar placeholder */}
      <header className="h-10 bg-bg-card border-b border-divider flex items-center px-4">
        <span className="text-text-secondary text-sm">鱿郁仔仔 v0.2.0</span>
      </header>
      {/* Main content */}
      <main className="flex-1 flex items-center justify-center">
        <p className="text-text-secondary">Phase 2 — P2-M1 脚手架启动成功</p>
      </main>
    </div>
  )
}
