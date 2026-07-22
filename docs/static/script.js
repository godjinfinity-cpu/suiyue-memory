(function () {
  const searchInput = document.querySelector("#archive-search");
  const grid = document.querySelector("#archive-grid");
  const filterButtons = document.querySelectorAll(".filter-button");

  if (!searchInput || !grid || filterButtons.length === 0) {
    return;
  }

  let activeFilter = "all";

  function updateArchive() {
    const keyword = searchInput.value.trim().toLowerCase();
    const cards = grid.querySelectorAll(".archive-card");

    cards.forEach((card) => {
      const visibility = card.getAttribute("data-visibility") || "";
      const text = card.getAttribute("data-search") || "";
      const matchesFilter = activeFilter === "all" || visibility === activeFilter;
      const matchesSearch = keyword.length === 0 || text.includes(keyword);

      card.hidden = !(matchesFilter && matchesSearch);
    });
  }

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      activeFilter = button.getAttribute("data-filter") || "all";
      filterButtons.forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      updateArchive();
    });
  });

  searchInput.addEventListener("input", updateArchive);
})();
