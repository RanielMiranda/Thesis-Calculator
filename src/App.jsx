import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import { MathJaxContext } from "better-react-mathjax";
import Homepage from "./Pages/HomePage/HomePage";
import Solver from "./Pages/Solver/Solver";


function App() {
return (
      <Router>
        <MathJaxContext>
            <Routes>
              <Route path="/" element={<Homepage />} />
              <Route path="/solver" element={<Solver />} />
            </Routes>
        </MathJaxContext>
      </Router>
  );
}

export default App;