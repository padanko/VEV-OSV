use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::fs::{self as tokio_fs};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::Mutex;
use tokio::time::{sleep, Duration};


const TITLE: &str = "EXAMPLE";
const DESCRIPTION: &str = "HELLO, WORLD";


#[derive(Serialize, Deserialize)]
struct Response {
    name: String,
    text: String,
    id: String,
    timestamp: String
}


#[derive(Serialize, Deserialize)]
struct Thread {
    thrid: String,
    title: String,
    contents: Vec<Response>,
}

#[derive(Serialize, Deserialize)]
struct Post_Format {
    thrid: String,
    data: Response,
}



type ThreadMap = Arc<Mutex<HashMap<String, Thread>>>;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let listener = TcpListener::bind(":::8282").await?;
    let thread_map: ThreadMap = Arc::new(Mutex::new(HashMap::new()));

    println!("Server listening on 127.0.0.1:8282");

    loop {
        let (socket, _) = listener.accept().await?;
        let thread_map = Arc::clone(&thread_map);

        tokio::spawn(async move {
            if let Err(e) = handle_client(socket, thread_map).await {
                eprintln!("Error handling client: {}", e);
            }
        });
    }
}

async fn handle_client(mut socket: TcpStream, thread_map: ThreadMap) -> Result<(), Box<dyn std::error::Error>> {
    let mut buffer = Vec::new();
    let mut temp_buf = [0u8; 1024];

    while let Ok(n) = socket.read(&mut temp_buf).await {
        if n == 0 {
            break;
        }
        buffer.extend_from_slice(&temp_buf[..n]);
        if let Some(pos) = buffer.windows(5).position(|w| w == b"<END>") {
            buffer.truncate(pos);
            break;
        }
    }

    let request = String::from_utf8_lossy(&buffer).to_string();

    println!("{}", request);

    if request == "getall" {
        let threads = get_all_threads().await?;
        let response = json!({
            "title": TITLE,
            "description": DESCRIPTION,
            "threads": threads
        });
        socket.write_all(response.to_string().as_bytes()).await?;
    } else if request.starts_with("makethr") {
        let mut thread_data: Thread = serde_json::from_str(&request[7..])?;
        thread_data.contents[0].id = String::from("???");
        save_thread(&thread_data).await?;
    } else if request.starts_with("get-thr") {
        let thrid = &request[7..];
        if let Some(response) = get_thread(thrid).await {
            socket.write_all(response.as_bytes()).await?;
        }
    } else if request.starts_with("postthr") {
        let mut post_data: Post_Format = serde_json::from_str(&request[7..])?;
        post_data.data.id = String::from("???");
        add_post_to_thread(&post_data.thrid, post_data.data).await?;
    } else if request.starts_with("pollthr") {
        let thrid = &request[7..];
        if let Some(mut old) = get_thread_nonsuffix(thrid).await {
            let mut new = String::new();
            loop {
                new = get_thread_nonsuffix(thrid).await.unwrap_or("{}".into());
                
                let old_thread: Thread = serde_json::from_str(&old)?;
                let new_thread: Thread = serde_json::from_str(&new)?;

                if old_thread.contents.len() < new_thread.contents.len() {
                    socket.write_all(format!("{}<END>",new).as_bytes()).await?;
                }


                old = new;
                sleep(Duration::from_millis(240)).await;
            }


        }
    }

    Ok(())
}

async fn get_all_threads() -> Result<Vec<Value>, Box<dyn std::error::Error>> {
    let mut threads = Vec::new();
    let paths = tokio_fs::read_dir("./BBS").await?;

    let mut dir = paths;
    while let Ok(Some(entry)) = dir.next_entry().await {
        if let Ok(thread) = tokio_fs::read_to_string(entry.path()).await {
            let thread: Thread = serde_json::from_str(&thread)?;
            threads.push(json!({
                "id": thread.thrid,
                "title": thread.title,
                "counter": thread.contents.len()
            }));
        }
    }

    Ok(threads)
}

async fn save_thread(thread: &Thread) -> Result<(), Box<dyn std::error::Error>> {
    let path = format!("./BBS/{}.json", thread.thrid);
    let data = serde_json::to_string(thread)?;
    tokio_fs::write(path, data).await?;
    Ok(())
}

async fn get_thread(thrid: &str) -> Option<String> {
    let path = format!("./BBS/{}.json", thrid);
    match tokio_fs::read_to_string(path).await {
        Ok(contents) => Some(contents + "<END>"),
        Err(_) => None,
    }
}

async fn get_thread_nonsuffix(thrid: &str) -> Option<String> {
    let path = format!("./BBS/{}.json", thrid);
    match tokio_fs::read_to_string(path).await {
        Ok(contents) => Some(contents),
        Err(_) => None,
    }
}

async fn add_post_to_thread(thrid: &str, data: Response) -> Result<(), Box<dyn std::error::Error>> {
    let path = format!("./BBS/{}.json", thrid);
    let mut thread: Thread = {
        let contents = tokio_fs::read_to_string(&path).await?;
        serde_json::from_str(&contents)?
    };

    thread.contents.push(data);
    let new_data = serde_json::to_string(&thread)?;
    tokio_fs::write(path, new_data).await?;

    Ok(())
}
