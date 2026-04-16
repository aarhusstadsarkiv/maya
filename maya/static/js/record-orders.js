import { asyncLogError } from "/static/js/error.js";
import { Requests } from "/static/js/requests.js";
import { Flash } from "/static/js/flash.js";
import { config } from "/static/js/config.js";

const spinner = document.querySelector(".loadingspinner");
const actionLinksElem = document.querySelector(".action-links");
const orderMessageElem = document.querySelector(".order-message");

if (actionLinksElem && orderMessageElem) {
    const state = {
        recordId: actionLinksElem.dataset.orderRecordId || "",
        orderId: actionLinksElem.dataset.orderId || "",
        hasActiveOrder: actionLinksElem.dataset.hasActiveOrder === "true",
        canRenewOrder: actionLinksElem.dataset.canRenewOrder === "true",
        isLoading: false,
        message: orderMessageElem.innerHTML,
        labels: {
            create: actionLinksElem.dataset.createLabel || "",
            delete: actionLinksElem.dataset.deleteLabel || "",
            renew: actionLinksElem.dataset.renewLabel || "",
        },
    };

    function setLoading(isLoading) {
        state.isLoading = isLoading;
        if (spinner) {
            spinner.classList.toggle("hidden", !isLoading);
        }
        render();
    }

    function createActionLink({ id, action, label, className = "", dataAttribute = "data-id", value = "" }) {
        const actionLink = document.createElement("a");
        actionLink.id = id;
        actionLink.href = "";
        actionLink.dataset.action = action;
        actionLink.textContent = label;

        if (className) {
            actionLink.className = className;
        }

        if (value) {
            actionLink.setAttribute(dataAttribute, value);
        }

        if (state.isLoading) {
            actionLink.setAttribute("aria-disabled", "true");
        }

        return actionLink;
    }

    function render() {
        const bookmarkElem = actionLinksElem.querySelector("#bookmark-action");
        actionLinksElem.replaceChildren();

        if (bookmarkElem) {
            actionLinksElem.appendChild(bookmarkElem);
        }

        if (!state.recordId) {
            orderMessageElem.innerHTML = state.message;
            return;
        }

        const orderActionLink = state.hasActiveOrder
            ? createActionLink({
                id: "record-order",
                action: "delete",
                label: state.labels.delete,
                className: "delete-order",
                value: state.recordId,
            })
            : createActionLink({
                id: "record-order",
                action: "create",
                label: state.labels.create,
                value: state.recordId,
            });
        actionLinksElem.appendChild(orderActionLink);

        if (state.hasActiveOrder && state.canRenewOrder && state.orderId) {
            const renewActionLink = createActionLink({
                id: "record-renew-order",
                action: "renew",
                label: state.labels.renew,
                dataAttribute: "data-orderid",
                value: state.orderId,
            });
            actionLinksElem.appendChild(renewActionLink);
        }

        orderMessageElem.innerHTML = state.message;
    }

    async function handleCreateOrder() {
        const res = await Requests.asyncPostJson(`/order/${state.recordId}`, {});
        if (res.error) {
            Flash.setMessage(res.message, "error");
            return;
        }

        state.hasActiveOrder = true;
        state.canRenewOrder = false;
        state.message = res.order_message || "";
        Flash.setMessage(res.message, "success");
        render();
    }

    async function handleDeleteOrder() {
        const confirmedDelete = confirm("Er du sikker på at du vil slette bestillingen?");
        if (!confirmedDelete) {
            return;
        }

        const res = await Requests.asyncPostJson(`/order/patch/${state.recordId}/record-id`, {});
        if (res.error) {
            Flash.setMessage(res.message, "error");
            return;
        }

        state.hasActiveOrder = false;
        state.canRenewOrder = false;
        state.orderId = "";
        state.message = "";
        Flash.setMessage(res.message, "success");
        render();
    }

    async function handleRenewOrder() {
        const res = await Requests.asyncPostJson(`/order/patch/${state.orderId}/renew`, {});
        if (res.error) {
            Flash.setMessage(res.message, "error");
            return;
        }

        state.canRenewOrder = false;
        state.message = res.message;
        Flash.setMessage(res.message, "success");
        render();
    }

    actionLinksElem.addEventListener("click", async function (event) {
        const actionElem = event.target.closest("#record-order, #record-renew-order");
        if (!actionElem || state.isLoading) {
            return;
        }

        event.preventDefault();
        setLoading(true);

        try {
            const action = actionElem.dataset.action;

            if (action === "create") {
                await handleCreateOrder();
            } else if (action === "delete") {
                await handleDeleteOrder();
            } else if (action === "renew") {
                await handleRenewOrder();
            }
        } catch (e) {
            Flash.setMessage(config.jsExceptionMessage, "error");
            asyncLogError(e);
            console.error(e);
        } finally {
            setLoading(false);
        }
    });

    render();
}
