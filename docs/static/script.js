(function () {
  const searchInput = document.querySelector("#archive-search");
  const grid = document.querySelector("#archive-grid");
  const filterButtons = document.querySelectorAll(".filter-button");

  if (!searchInput || !grid || filterButtons.length === 0) {
    return;
  }

  let activeFilter = "all";
  const emptyState = document.querySelector("#archive-empty");

  function updateArchive() {
    const keyword = searchInput.value.trim().toLowerCase();
    const cards = grid.querySelectorAll(".archive-card");

    let visibleCount = 0;
    cards.forEach((card) => {
      const media = card.getAttribute("data-media") || "";
      const text = card.getAttribute("data-search") || "";
      const matchesFilter = activeFilter === "all" || media === activeFilter;
      const matchesSearch = keyword.length === 0 || text.includes(keyword);

      card.hidden = !(matchesFilter && matchesSearch);
      if (!card.hidden) visibleCount += 1;
    });
    if (emptyState) emptyState.hidden = visibleCount > 0;
  }

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      activeFilter = button.getAttribute("data-filter") || "all";
      filterButtons.forEach((item) => {
        item.classList.remove("is-active");
        item.setAttribute("aria-pressed", "false");
      });
      button.classList.add("is-active");
      button.setAttribute("aria-pressed", "true");
      updateArchive();
    });
  });

  searchInput.addEventListener("input", updateArchive);
})();
