---
layout: page
title: "전체 글 보기"
permalink: /all-posts/
---

최근 업데이트된 모든 꿀팁과 리뷰를 확인해 보세요! 👇

<div class="all-posts-list">
  <ul>
    {% for post in site.posts %}
      <li style="margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 15px;">
        <span style="color: #888; font-size: 0.9em;">{{ post.date | date: "%Y-%m-%d" }}</span><br/>
        <a href="{{ post.url | relative_url }}" style="font-size: 1.1em; font-weight: bold; color: #2c3e50; text-decoration: none;">
          {{ post.title }}
        </a>
      </li>
    {% endfor %}
  </ul>
</div>
