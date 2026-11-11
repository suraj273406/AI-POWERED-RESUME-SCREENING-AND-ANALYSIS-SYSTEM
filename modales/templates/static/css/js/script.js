
document.addEventListener("DOMContentLoaded", function () {

    console.log(
        "AI Resume Screening System Started"
    );

    const fileInput = document.querySelector(
        'input[name="resume"]'
    );

    if (fileInput) {

        fileInput.addEventListener("change", function () {

            if (this.files.length > 0) {

                const file = this.files[0];

                const allowedExtensions = [
                    "pdf",
                    "docx"
                ];

                const extension = file.name
                    .split(".")
                    .pop()
                    .toLowerCase();

                if (!allowedExtensions.includes(extension)) {

                    alert("Please upload PDF or DOCX file.");

                    this.value = "";
                    return;
                }

                if (file.size > 10 * 1024 * 1024) {

                    alert("Maximum file size is 10 MB.");

                    this.value = "";
                    return;
                }

                console.log(
                    "Selected resume:",
                    file.name
                );
            }
        });
    }

});
