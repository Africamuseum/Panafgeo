import asyncio
import httpx

class QwenPipeline:
    def __init__(self, qwen, timeout, max_concurrent_requests):
        self.qwen = qwen
        self.timeout = timeout
        self.max_concurrent_requests = max_concurrent_requests

    async def run(self, img_paths_list, url64_list):
        """
        Extract the text of each image with Qwen, sending requests concurrently to the vLLM server.
    
        A single asynchronous HTTP client sends one request per image, and the server
        handles them concurrently through continuous batching. All responses are
        gathered and stored in extracted_data_list.
    
        Args:
            img_paths_list (list[str]): Paths of the images to process.
            url64_list (list[str]): Base64-encoded images, in the same order as
                img_paths_list.
        Returns:
            list[dict]: List of dictionaries containing all the data extracted from images.
        """
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async with httpx.AsyncClient(timeout=self.timeout, limits=httpx.Limits(max_connections=self.max_concurrent_requests)) as client:

            async def limited(img_path, url64):
                async with semaphore:
                    return await self.qwen.extract_text(client, img_path, url64)
                    
            tasks = [limited(img_path, url64) for img_path, url64 in zip(img_paths_list, url64_list)]
            
            extracted_data_list = await asyncio.gather(*tasks, return_exceptions=True)
            return extracted_data_list