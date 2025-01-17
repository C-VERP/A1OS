/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Component} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

export const standardErrorDialogProps = {
    traceback: { type: [String, { value: null }], optional: true },
    message: { type: String, optional: true },
    name: { type: String, optional: true },
    exceptionName: { type: [String, { value: null }], optional: true },
    data: { type: [Object, { value: null }], optional: true },
    subType: { type: [String, { value: null }], optional: true },
    code: { type: [Number, String, { value: null }], optional: true },
    type: { type: [String, { value: null }], optional: true },
    close: Function, // prop added by the Dialog service
};

// -----------------------------------------------------------------------------
// MarketplaceErrorDialog Dialog
// -----------------------------------------------------------------------------

export class MarketplaceErrorDialog extends Component {
    setup() {
        const { data, subType } = this.props;
        const [message, title, additionalContext] = data.arguments;
        this.title = _t(title) || _t(this.getRandomErrorTitle());
        this.message = _t(message);
        this.additionalContext = additionalContext;
        this.traceback = this.props.traceback;
        if (this.props.data && this.props.data.debug) {
            this.traceback = `${this.props.data.debug}\nThe above server error caused the following client error:\n${this.traceback}`;
        }
    }

    getRandomErrorTitle() {
        const errorTitles = [
          "Oh snap!",
          "Oops!",
          "Uh-oh!",
          "Error!",
          "Yikes!",
          "Whoops!",
          "Houston, we have a problem!",
          "Oh no!",
          "Epic fail!",
        ];
        const randomIndex = Math.floor(Math.random() * errorTitles.length);
        return errorTitles[randomIndex];
    }

    onClickClipboard() {
        browser.navigator.clipboard.writeText(
            `${this.props.message}\n${this.traceback}`
        );
    }
}
MarketplaceErrorDialog.template = "base_marketplace.MarketplaceErrorDialog";
MarketplaceErrorDialog.components = { Dialog };
MarketplaceErrorDialog.props = { ...standardErrorDialogProps };


registry
    .category("error_dialogs")
    .add("odoo.addons.base_marketplace.models.exceptions.MarketplaceException", MarketplaceErrorDialog)