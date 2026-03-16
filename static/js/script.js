/* buat button copy link bekerja */
function copyLink(button) {

    const url = window.location.href;

    navigator.clipboard.writeText(url);

    const originalText = button.innerText;

    button.innerText = "Link berhasil disalin ✓";

    setTimeout(() => {
        button.innerText = originalText;
    }, 2000);

}

/* buat bagian quill editor, jadi nanti teksnya bisa bold, italic, list, dll pas nulis narasi */
document.addEventListener("DOMContentLoaded", function () {

    const editor = document.querySelector("#editor");

    if (editor) {

        var quill = new Quill("#editor", {
            theme: "snow",
            placeholder: "Tulis ceritamu di sini...",
            modules: {
                toolbar: [
                    ["bold", "italic"],
                    ["blockquote"],
                    [{ list: "ordered" }, { list: "bullet" }],
                    ["link"]
                ]
            }
        });

        const form = document.querySelector("form");

        form.onsubmit = function () {

            document.querySelector("#content").value = quill.root.innerHTML;

        };

    }

});