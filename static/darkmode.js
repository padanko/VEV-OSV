
var isdark = localStorage.getItem("darkmode") == "true"

function dark_mode_change() {
    if ( isdark ) {
        document.querySelectorAll(".body").forEach((d)=>{
            d.style.backgroundColor = "#fff"
            d.style.color = "#111"
        })

    } else {
        document.querySelectorAll(".body").forEach((d)=>{
            d.style.backgroundColor = "#222"
            d.style.color = "#fff"
            
        })

    }
}

dark_mode_change()

$("#dark-change").click(()=>{
    isdark = !isdark
    dark_mode_change()
    localStorage.setItem("darkmode", isdark)
})