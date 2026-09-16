import { useState } from 'react';
import { Header, type ExplorerRoute } from './components/layout/Header';
import { StatusBanner } from './components/layout/StatusBanner';
import { Footer } from './components/layout/Footer';
import { ExplorerPage } from './pages/ExplorerPage';
import { ValidationPage } from './pages/ValidationPage';
import { useOceanExplorer } from './hooks/useOceanExplorer';

/**
 * OceanEmbed product shell: 3D explorer + separate scientific credibility page.
 * The explorer answers WHERE/WHEN/HOW DEEP/WHAT; Validation & Model answers WHY trust it.
 */
export default function App() {
  const explorer = useOceanExplorer();
  const [route, setRoute] = useState<ExplorerRoute>('explorer');

  return (
    <div className="flex min-h-[100dvh] flex-col bg-zinc-950 text-zinc-50">
      <Header route={route} onNavigate={setRoute} />
      <StatusBanner status={explorer.status} detail={explorer.bannerDetail} />
      <main className="flex min-h-0 flex-1 flex-col">
        {route === 'explorer' ? (
          <ExplorerPage explorer={explorer} />
        ) : (
          <ValidationPage availability={explorer.availability} />
        )}
      </main>
      <Footer />
    </div>
  );
}
