odoo.define(
  "crm_field_rename.hawk_button",
  ["@web/core/utils/hooks"],
  function (hooks) {
    "use strict";

    const { Component, onMounted, useRef, xml } = owl;

    class HawkButton extends Component {
      setup() {
        super.setup();
        this.buttonRef = useRef("hawkButton");

        onMounted(() => {
          // Find all CRM lead views and add the button
          const addButton = () => {
            // For list view
            const listAddButton = document.querySelector(".o_list_button_add");
            if (listAddButton && window.location.href.includes("crm.lead")) {
              const hawkButton = document.createElement("button");
              hawkButton.className = "btn btn-primary mx-1";
              hawkButton.textContent = "Hawk Tuah";
              hawkButton.onclick = () => alert("Hawk Tuah button clicked!");

              if (!document.querySelector(".hawk-tuah-button")) {
                hawkButton.classList.add("hawk-tuah-button");
                listAddButton.parentNode.insertBefore(
                  hawkButton,
                  listAddButton.nextSibling
                );
              }
            }
          };

          // Initial check
          addButton();

          // Set up a mutation observer to watch for DOM changes
          const observer = new MutationObserver(() => {
            setTimeout(addButton, 500);
          });

          observer.observe(document.body, {
            childList: true,
            subtree: true,
          });
        });
      }
    }

    // Register the component
    HawkButton.template = xml`<div/>`;

    return HawkButton;
  }
);
