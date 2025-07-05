import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
    apiKey: "AIzaSyC5etEVjVW7T7HgHfpICFWXTkOBWLWRD_A",
    authDomain: "skyward-aae9b.firebaseapp.com",
    projectId: "skyward-aae9b",
    storageBucket: "skyward-aae9b.firebasestorage.app",
    messagingSenderId: "602358973762",
    appId: "1:602358973762:web:26a1309ef62e9c93e374db"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase services
export const auth = getAuth(app);
export const db = getFirestore(app);

export default app; 