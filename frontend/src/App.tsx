import { useCallback } from 'react';
import AuthForm from './components/AuthForm';
import Discovery from './components/Discovery';
import HealthStatus from './components/HealthStatus';
import { ErrorNotice, Loading } from './components/Feedback';
import { useSession } from './hooks/useSession';
import { useTeamCreation } from './hooks/useTeamCreation';
import { useAdmission } from './hooks/useAdmission';
import { useInvitations } from './hooks/useInvitations';
import { useDiscoveryNavigation } from './hooks/useDiscoveryNavigation';
import { useLifecycle } from './hooks/useLifecycle';

export default function App() {
  const auth = useSession();
  const navigation = useDiscoveryNavigation(auth.state.status === 'authenticated' ? auth.state.session.identity.user_id :
    auth.state.status === 'guest' || auth.state.status === 'ending' ? null : undefined);
  const creation = useTeamCreation(auth.state.status === 'authenticated' ? auth.state : null, auth.expired);
  const scope = auth.state.status === 'authenticated' ? auth.state : null;
  const admission = useAdmission(scope, auth.expired);
  const invitations = useInvitations(scope, auth.expired);
  const lifecycle = useLifecycle(scope, auth.expired);
  const signal = scope?.signal;
  const expireWorkspace = useCallback(() => { if (signal && !signal.aborted) auth.expired(); }, [signal, auth.expired]);
  return <>
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="site-header"><div className="header-inner">
      <a className="brand" href="#main" aria-label="Merge home"><span className="brand-mark" aria-hidden="true">m</span>merge<span className="brand-period">.</span></a>
      <span className="header-tagline">Better, together.</span>
      {auth.state.status === 'authenticated' && <div className="account"><span className="username">@{auth.state.session.identity.username}</span><button className="button secondary" onClick={() => { if (auth.state.status === 'authenticated') auth.logout(auth.state.session); }}>Sign out</button></div>}
    </div></header>
    <main id="main" className="app-main" tabIndex={-1}>
      {auth.state.status === 'checking' && <div className="center-state panel"><Loading>Restoring your session...</Loading></div>}
      {auth.state.status === 'error' && <div className="center-state panel"><h1>Let us reconnect.</h1><ErrorNotice error={auth.state.error} retry={auth.restore} /><p className="muted">We could not verify your session. Your workspace will stay hidden until we can.</p></div>}
      {auth.state.status === 'guest' && <AuthForm onSession={auth.accept} restore={auth.restore} message={auth.state.message} />}
      {auth.state.status === 'authenticated' && <Discovery key={auth.state.epoch} onExpired={expireWorkspace} creation={creation} admission={admission} invitations={invitations} lifecycle={lifecycle} restore={auth.restore} navigation={navigation.navigation} updateNavigation={navigation.update} />}
      {auth.state.status === 'ending' && <div className="center-state panel"><h1>Signing out</h1>{auth.state.error ? <>
        <ErrorNotice error={auth.state.error} retry={() => { if (auth.state.status === 'ending') auth.logout(auth.state.session); }} />
        <p>Sign-out is not confirmed. Your server session may still be active. Your workspace has been cleared from this view.</p>
        <button className="text-button" onClick={auth.restore}>Check session</button>
      </> : <Loading>Closing your session...</Loading>}</div>}
    </main>
    <footer className="site-footer"><span>Merge - Built for connection.</span><details><summary>Service status</summary><HealthStatus /></details></footer>
  </>;
}
