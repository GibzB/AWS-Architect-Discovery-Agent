import { useState } from 'react';
import { StartScreen } from './components/StartScreen';
import { Workshop } from './components/Workshop';
import './index.css';

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [customerName, setCustomerName] = useState('');

  if (!sessionId) {
    return (
      <StartScreen
        onSessionCreated={(id, name) => {
          setSessionId(id);
          setCustomerName(name);
        }}
      />
    );
  }

  return (
    <Workshop
      sessionId={sessionId}
      customerName={customerName}
      onReset={() => {
        setSessionId(null);
        setCustomerName('');
      }}
    />
  );
}

export default App;
