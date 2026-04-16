import { asyncLogError } from "/static/js/error.js";
import { Requests } from "/static/js/requests.js";
import { Flash } from "/static/js/flash.js";
import { config } from "/static/js/config.js";

const spinner = document.querySelector('.loadingspinner');
const orderElem = document.getElementById('record-order');
const orderMessageElem = document.querySelector('.order-message');
const orderRenewElem = document.getElementById('record-renew-order');

// <div class ="action-links"><a href="#" id="record-order" data-id="1">Bestil materialet</a></div>

if (orderElem) {

    orderElem.addEventListener('click', async function (event) {
        event.preventDefault();
        spinner.classList.toggle('hidden');
        let res;
        try {

            const recordId = orderElem.getAttribute('data-id');
            const action = orderElem.getAttribute('data-action');
            
            let url;
            let data;
            
            if (action === 'create') {

                url = `/order/${recordId}`;
                data = {}
            } else {
                url = `/order/patch/${recordId}/record-id`;
                data = {}

                const confirmedDelete = confirm('Er du sikker på at du vil slette bestillingen?');
                if (!confirmedDelete) {
                    return;
                }
            }

            res = await Requests.asyncPostJson(url, {});
            if (res.error) {
                Flash.setMessage(res.message, 'error');
            } else {

                if (action === 'delete') {
                    Flash.setMessage(res.message, 'success');
                    orderElem.innerText = 'Bestil til læsesal';
                    orderElem.setAttribute('data-action', 'create');
                    // Set class to empty
                    orderElem.className = '';
                    orderMessageElem.innerText = "";
                }

                if (action === 'create') {
                    Flash.setMessage(res.message, 'success');
                    orderElem.innerText = 'Afslut bestilling';
                    orderElem.setAttribute('data-action', 'delete');
                    // Set class to 'delete-order'
                    orderElem.className = 'delete-order';
                    orderMessageElem.innerHTML = res.order_message;
                }
            }

        } catch (e) {
            Flash.setMessage(config.jsExceptionMessage, 'error');
            asyncLogError(e);
            console.error(e);
        } finally {
            spinner.classList.toggle('hidden');
        }
    });
}


if (orderRenewElem) {
    orderRenewElem.addEventListener('click', async function (event) {
        event.preventDefault();
        spinner.classList.toggle('hidden');
        let res;
        try {
            const orderId = orderRenewElem.getAttribute('data-orderid');
            const url = `/order/patch/${orderId}/renew`;
            res = await Requests.asyncPostJson(url, {});
            if (res.error) {
                Flash.setMessage(res.message, 'error');
            } else {
                // Remove renew button
                orderRenewElem.remove();
                Flash.setMessage(res.message, 'success');
                orderMessageElem.innerHTML = res.message;
            }
        } catch (e) {
            Flash.setMessage(config.jsExceptionMessage, 'error');
            asyncLogError(e);
            console.error(e);
        } finally {
            spinner.classList.toggle('hidden');
        }
    });
}