// front-end js by romy

const mediaButton = document.getElementById("media-popup");
const timeButton = document.getElementById("time-popup");
const piButton = document.getElementById("pi-popup");
const gameButton = document.getElementById("abort-button");

const mediaPopup = document.querySelector(".media-hidden");
const timePopup = document.querySelector(".time-hidden");
const piPopup = document.querySelector(".pi-hidden");
const gamePopup = document.querySelector(".game-hidden");
const taskPopup = document.querySelector(".tasks-hidden");

const closeMediaButton = document.querySelector(".close-media");
const closeTimeButton = document.querySelector(".close-time");
const closePiButton = document.querySelector(".close-pi");
const closeGameButton = document.querySelector(".close-game");
const closeTasksButton = document.querySelector(".close-tasks");

const abortButton = document.querySelector(".abort-button");
const confirmButton = document.getElementById("end-game-button");
const startButton = document.getElementById("start-game-button");
const snoozeButton = document.getElementById("snooze-game-button");
const prepareButton = document.getElementById("prepare-game-button");
const abortPopup = document.querySelector(".abort");
const confirmPopup = document.querySelector(".confirmation");

/* media */

mediaButton.addEventListener("click", () => {
  mediaPopup.classList.remove("hidden");
  mediaPopup.classList.add("shown");
});

closeMediaButton.addEventListener("click", () => {
  mediaPopup.classList.remove("shown");
  mediaPopup.classList.add("hidden");
});

/* time */

timeButton.addEventListener("click", () => {
  timePopup.classList.remove("hidden");
  timePopup.classList.add("shown");
});

closeTimeButton.addEventListener("click", () => {
  timePopup.classList.remove("shown");
  timePopup.classList.add("hidden");
});

/* pi */

piButton.addEventListener("click", () => {
  piPopup.classList.remove("hidden");
  piPopup.classList.add("shown");
});

closePiButton.addEventListener("click", () => {
  piPopup.classList.remove("shown");
  piPopup.classList.add("hidden");
});

/* game */

gameButton.addEventListener("click", () => {
  gamePopup.classList.remove("hidden");
  gamePopup.classList.add("shown");
});

closeGameButton.addEventListener("click", () => {
  gamePopup.classList.remove("shown");
  gamePopup.classList.add("hidden");

  confirmPopup.classList.remove("shown");
  confirmPopup.classList.add("hidden");

  abortPopup.classList.remove("message-shown");
  abortPopup.classList.add("hidden");
});

/* abort */

abortButton.addEventListener("click", () => {
  abortPopup.classList.remove("hidden");
  abortPopup.classList.add("message-shown");
});

confirmButton.addEventListener("click", () => {
  abortPopup.classList.remove("message-shown");
  abortPopup.classList.add("hidden");

  confirmPopup.classList.remove("hidden");
  confirmPopup.classList.add("shown");

  gamePopup.classList.remove("shown");
  gamePopup.classList.add("hidden");
});

startButton.addEventListener("click", () => {
  confirmPopup.classList.remove("shown");
  confirmPopup.classList.add("hidden");

  gamePopup.classList.remove("shown");
  gamePopup.classList.add("hidden");
});

snoozeButton.addEventListener("click", () => {
  confirmPopup.classList.remove("shown");
  confirmPopup.classList.add("hidden");

  gamePopup.classList.remove("shown");
  gamePopup.classList.add("hidden");
});

prepareButton.addEventListener("click", () => {
  confirmPopup.classList.remove("shown");
  confirmPopup.classList.add("hidden");

  gamePopup.classList.remove("shown");
  gamePopup.classList.add("hidden");
});
/* tasks */

piButton.addEventListener("click", () => {
  piPopup.classList.remove("hidden");
  piPopup.classList.add("shown");
});

closePiButton.addEventListener("click", () => {
  piPopup.classList.remove("shown");
  piPopup.classList.add("hidden");
});
// document.addEventListener("DOMContentLoaded", function () {
//   let navbarContainer = document.getElementById("navbar-container");
//   let lastScrollY = window.scrollY;

//   function updateNavbarPosition() {
//       let currentScrollY = window.scrollY;
//       if (currentScrollY > lastScrollY) {
//           // Scrolling down, make the navbar sticky
//           navbarContainer = "sticky";
//       } else {
//           // Scrolling up, make the navbar absolute
//           navbarContainer = "absolute";
//       }
//       lastScrollY = currentScrollY;
//   }

//   window.addEventListener("scroll", updateNavbarPosition);
// });