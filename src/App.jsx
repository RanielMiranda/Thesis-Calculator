import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import { MathJaxContext } from "better-react-mathjax";
import Solver from "./Pages/Solver/Solver";
import Notes from "./Pages/Notes/Notes";



function App() {
  return (
    <Router>
      <div className="flex flex-col min-h-screen">
        <div className="flex justify-center items-center w-screen pt-16">
          <Routes>
            <Route path="/" element={<Solver />} />
            <Route path="/notes" element={<Notes />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
