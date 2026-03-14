import { ChatPanel } from "./components/ChatPanel";
import { FlowPanel } from "./components/FlowPanel";
import "./App.css";

export function App() {
  return (
    <div className="app-layout">
      <ChatPanel />
      <FlowPanel />
    </div>
  );
}
