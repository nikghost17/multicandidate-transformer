import { createContext, useContext, useState } from "react";

const DrawerContext = createContext(null);

export function DrawerProvider({ children }) {
  const [openCandidate, setOpenCandidate] = useState(null);

  const openDrawer  = (candidate) => setOpenCandidate(candidate);
  const closeDrawer = ()          => setOpenCandidate(null);

  return (
    <DrawerContext.Provider value={{ openCandidate, openDrawer, closeDrawer }}>
      {children}
    </DrawerContext.Provider>
  );
}

export const useDrawer = () => useContext(DrawerContext);
